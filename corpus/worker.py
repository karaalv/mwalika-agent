"""
This module contains the worker used to push
data into QdrantDB and MongoDB. It handles all
preprocessing and transformation of data before it is
stored in the databases.
"""

import asyncio
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import TypeVar

from tqdm import tqdm

from corpus.utils import read_json
from databases.mongodb.main import (
	MongoDBCollection,
	get_collection,
)
from databases.qdrant.collections import (
	ensure_collection_exists,
)
from databases.qdrant.points import create_points
from openai_client.main import (
	create_embedding,
	normal_response,
)
from schemas.corpus.agencies import AgencyEntry
from schemas.corpus.departments import DepartmentEntry
from schemas.corpus.faqs import FAQEntry
from schemas.corpus.ministries import MinistryEntry
from schemas.corpus.qdrant import (
	CorpusItem,
	CorpusItemType,
	CorpusPayload,
)
from schemas.corpus.services import ServiceEntry
from shared.ids import generate_uuid_str
from shared.logging import LogStyle, cprint

T = TypeVar('T')

# --- Constants and utilities ---

_description_summary_prompt = dedent("""
You are a summarisation engine used for corpus compression.

Your task is to shorten government service, agency, or
ministry descriptions to a maximum of 150 tokens.

Rules:
- Preserve all critical factual information.
- Do NOT invent, infer, or add new details.
- Do NOT generalise beyond the provided text.
- Remove redundancy, marketing language, and filler phrases.
- Maintain a neutral, formal tone.
- Keep proper nouns and official terminology intact.
- Output only the shortened description.
- Do not include explanations, commentary, or formatting.

If the input is already concise, return it unchanged.
""").strip()

BATCH_SIZE = 500


@dataclass(frozen=True)
class PointJob:
	"""
	Represents a unit of work for creating a
	point in Qdrant. Particularly for forming
	the embedding.
	"""

	qdrant_id: str
	entity_id: str
	corpus_type: CorpusItemType
	embedding_input: str


def chunked(
	items: Iterable[T],
	size: int = BATCH_SIZE,
) -> Iterator[list[T]]:
	"""
	Splits an iterable of items into
	batches of a specified size.
	"""
	if size <= 0:
		raise ValueError('size must be > 0')

	batch: list[T] = []

	for item in items:
		batch.append(item)
		if len(batch) == size:
			yield batch
			batch = []

	if batch:
		yield batch


# --- Worker Class ---


class CorpusWorker:
	def __init__(self, data_path) -> None:
		# Configuration
		self.data_path: Path = data_path

		# Entity states
		self.ministries: dict[str, MinistryEntry] = {}
		self.departments: dict[str, DepartmentEntry] = {}
		self.agencies: dict[str, AgencyEntry] = {}
		self.services: dict[str, ServiceEntry] = {}
		self.faqs: dict[str, FAQEntry] = {}

		# Load data from JSON files into memory
		self.load_data()

	# --- Loaders for each entity type ---

	def load_data(self) -> None:
		cprint(
			'Loading corpus data from JSON files...',
			style=LogStyle.INFO,
		)
		self._load_ministries()
		self._load_departments()
		self._load_agencies()
		self._load_services()
		self._load_faqs()

	def _load_ministries(self) -> None:
		data: list[dict] = read_json(
			self.data_path / 'ministries.json'
		)
		# Parse and store ministries
		for entry in data:
			ministry = MinistryEntry.model_validate(entry)
			self.ministries[ministry.ministry_id] = ministry

	def _load_departments(self) -> None:
		data: list[dict] = read_json(
			self.data_path / 'departments.json'
		)
		for entry in data:
			department = DepartmentEntry.model_validate(entry)
			self.departments[department.department_id] = department

	def _load_agencies(self) -> None:
		data: list[dict] = read_json(self.data_path / 'agencies.json')
		for entry in data:
			agency = AgencyEntry.model_validate(entry)
			self.agencies[agency.agency_id] = agency

	def _load_services(self) -> None:
		data: list[dict] = read_json(self.data_path / 'services.json')
		for entry in data:
			service = ServiceEntry.model_validate(entry)
			self.services[service.service_id] = service

	def _load_faqs(self) -> None:
		data: list[dict] = read_json(self.data_path / 'faqs.json')
		for entry in data:
			faq = FAQEntry.model_validate(entry)
			self.faqs[faq.faq_id] = faq

	# --- Processing helpers ---

	def _get_ministry_departments(
		self, ministry_id: str
	) -> list[DepartmentEntry]:
		return [
			dept
			for dept in self.departments.values()
			if dept.ministry_id == ministry_id
		]

	def _get_department_agencies(
		self, department_id: str
	) -> list[AgencyEntry]:
		return [
			agency
			for agency in self.agencies.values()
			if agency.department_id == department_id
		]

	def _get_agency_services(
		self, agency_id: str
	) -> list[ServiceEntry]:
		return [
			service
			for service in self.services.values()
			if service.agency_id == agency_id
		]

	# --- Qdrant helpers ---

	async def _summarise_description(self, text: str) -> str:
		return await normal_response(
			system_prompt=_description_summary_prompt,
			user_input=text,
		)

	async def _precompute_summaries(self) -> None:
		"""
		Precompute summaries for all descriptions
		that exceed the token limit
		"""
		cprint(
			'Precomputing summaries for long descriptions...',
			style=LogStyle.INFO,
		)

		async def do_min(m: MinistryEntry) -> None:
			if not m.ministry_description:
				return
			if len(m.ministry_description.split()) > 150:
				m.ministry_description_summary = (
					await self._summarise_description(
						m.ministry_description
					)
				)
			else:
				m.ministry_description_summary = (
					m.ministry_description
				)

		async def do_ag(a: AgencyEntry) -> None:
			if not a.agency_description:
				return
			if len(a.agency_description.split()) > 150:
				a.agency_description_summary = (
					await self._summarise_description(
						a.agency_description
					)
				)
			else:
				a.agency_description_summary = a.agency_description

		sem = asyncio.Semaphore(8)

		total = len(self.ministries) + len(self.agencies)

		with tqdm(
			total=total,
			desc='Precomputing summaries',
			unit='item',
		) as pbar:

			async def guarded(coro):
				async with sem:
					result = await coro
					pbar.update(1)
					return result

			tasks = []

			for m in self.ministries.values():
				tasks.append(asyncio.create_task(guarded(do_min(m))))

			for a in self.agencies.values():
				tasks.append(asyncio.create_task(guarded(do_ag(a))))

			await asyncio.gather(*tasks)

	async def _run_point_job(
		self,
		job: PointJob,
	) -> CorpusItem:
		"""
		Runs a PointJob by creating the embedding
		and forming the CorpusItem to be stored in
		Qdrant.
		"""
		embedding = await create_embedding(input=job.embedding_input)
		return CorpusItem(
			id=job.qdrant_id,
			vector=embedding,
			payload=CorpusPayload(
				type=job.corpus_type,
				schema_version='1.0',
				entity_id=job.entity_id,
			),
		)

	async def _build_point_jobs(self) -> list[PointJob]:
		jobs: list[PointJob] = []
		for ministry in self.ministries.values():
			# Form ministry context for embedding input
			min_desc = ministry.ministry_description
			min_sum = ministry.ministry_description_summary
			if not min_sum:
				min_sum = min_desc

			ministry_ctx = (
				f'Ministry: {ministry.ministry_name}\n'
				f'Description: {min_sum}\n'
			)

			# Generate UUID for Qdrant point ID
			ministry_qdrant_id = generate_uuid_str()
			ministry.qdrant_id = ministry_qdrant_id

			# Add ministry job
			jobs.append(
				PointJob(
					qdrant_id=ministry_qdrant_id,
					entity_id=ministry.ministry_id,
					corpus_type=CorpusItemType.MINISTRY,
					embedding_input=ministry_ctx,
				)
			)

			# Departments
			departments = self._get_ministry_departments(
				ministry.ministry_id
			)
			for department in departments:
				dept_ctx = (
					ministry_ctx
					+ f'\nDepartment: {department.department_name}\n'  # noqa: E501
				)

				department_qdrant_id = generate_uuid_str()
				department.qdrant_id = department_qdrant_id

				jobs.append(
					PointJob(
						qdrant_id=department_qdrant_id,
						entity_id=department.department_id,
						corpus_type=CorpusItemType.DEPARTMENT,
						embedding_input=dept_ctx,
					)
				)

				# Agencies
				agencies = self._get_department_agencies(
					department.department_id
				)
				for agency in agencies:
					ag_desc = agency.agency_description
					ag_sum = agency.agency_description_summary
					if not ag_sum:
						ag_sum = ag_desc

					ag_ctx = (
						dept_ctx + f'\nAgency: {agency.agency_name}\n'  # noqa: E501
						f'Agency Description: {ag_sum}\n'
					)

					agency_qdrant_id = generate_uuid_str()
					agency.qdrant_id = agency_qdrant_id

					jobs.append(
						PointJob(
							qdrant_id=agency_qdrant_id,
							entity_id=agency.agency_id,
							corpus_type=CorpusItemType.AGENCY,
							embedding_input=ag_ctx,
						)
					)

					# Services
					services = self._get_agency_services(
						agency.agency_id
					)
					for service in services:
						svc_ctx = (
							ag_ctx
							+ f'\nService: {service.service_name}\n'  # noqa: E501
						)

						service_qdrant_id = generate_uuid_str()
						service.qdrant_id = service_qdrant_id

						jobs.append(
							PointJob(
								qdrant_id=service_qdrant_id,
								entity_id=service.service_id,
								corpus_type=CorpusItemType.SERVICE,
								embedding_input=svc_ctx,
							)
						)
		return jobs

	async def _form_qdrant_points(self) -> list[CorpusItem]:
		"""
		Form corpus points by processing all entities
		and creating embeddings.
		"""
		total_items = (
			len(self.ministries)
			+ len(self.departments)
			+ len(self.agencies)
			+ len(self.services)
		)

		await self._precompute_summaries()
		jobs = await self._build_point_jobs()
		points: list[CorpusItem] = []

		with tqdm(
			total=total_items,
			desc='Forming Qdrant points',
			unit='item',
		) as pbar:

			async def worker(job: PointJob):
				point = await self._run_point_job(job)
				pbar.update(1)
				return point

			# Batch jobs
			for batch in chunked(jobs, size=100):
				results = await asyncio.gather(
					*(worker(job) for job in batch)
				)
				points.extend(results)
		return points

	# --- Qdrant operations ---

	async def _ensure_qdrant_collection(self) -> None:
		await ensure_collection_exists()

	async def _push_to_qdrant(self) -> None:
		cprint(
			'Forming Qdrant points from corpus data...',
			style=LogStyle.INFO,
		)
		points = await self._form_qdrant_points()

		cprint(
			f'Pushing {len(points)} points to Qdrant...',
			style=LogStyle.INFO,
		)
		with tqdm(
			total=len(points),
			desc='Pushing to Qdrant',
			unit='point',
		) as pbar:
			for batch in chunked(points):
				await create_points(batch)
				pbar.update(len(batch))

	# --- MongoDB operations ---

	async def _push_ministries_to_mongodb(self) -> None:
		cprint(
			'Pushing ministries to MongoDB...',
			style=LogStyle.INFO,
		)
		ministry_collection = await get_collection(
			MongoDBCollection.MINISTRIES
		)
		ministries = [
			ministry.model_dump()
			for ministry in self.ministries.values()
		]
		with tqdm(
			total=len(self.ministries),
			desc='Pushing ministries to MongoDB',
			unit='document',
		) as pbar:
			for batch in chunked(ministries):
				await ministry_collection.insert_many(batch)
				pbar.update(len(batch))

	async def _push_departments_to_mongodb(self) -> None:
		cprint(
			'Pushing departments to MongoDB...',
			style=LogStyle.INFO,
		)
		department_collection = await get_collection(
			MongoDBCollection.DEPARTMENTS
		)
		departments = [
			department.model_dump()
			for department in self.departments.values()
		]
		with tqdm(
			total=len(self.departments),
			desc='Pushing departments to MongoDB',
			unit='document',
		) as pbar:
			for batch in chunked(departments):
				await department_collection.insert_many(batch)
				pbar.update(len(batch))

	async def _push_agencies_to_mongodb(self) -> None:
		cprint(
			'Pushing agencies to MongoDB...',
			style=LogStyle.INFO,
		)
		agency_collection = await get_collection(
			MongoDBCollection.AGENCIES
		)
		agencies = [
			agency.model_dump() for agency in self.agencies.values()
		]
		with tqdm(
			total=len(self.agencies),
			desc='Pushing agencies to MongoDB',
			unit='document',
		) as pbar:
			for batch in chunked(agencies):
				await agency_collection.insert_many(batch)
				pbar.update(len(batch))

	async def _push_services_to_mongodb(self) -> None:
		cprint(
			'Pushing services to MongoDB...',
			style=LogStyle.INFO,
		)
		service_collection = await get_collection(
			MongoDBCollection.SERVICES
		)
		services = [
			service.model_dump() for service in self.services.values()
		]
		with tqdm(
			total=len(self.services),
			desc='Pushing services to MongoDB',
			unit='document',
		) as pbar:
			for batch in chunked(services):
				await service_collection.insert_many(batch)
				pbar.update(len(batch))

	async def _push_to_mongodb(self) -> None:
		await self._push_ministries_to_mongodb()
		await self._push_departments_to_mongodb()
		await self._push_agencies_to_mongodb()
		await self._push_services_to_mongodb()

	# --- Main run method ---

	async def run(self) -> None:
		await self._ensure_qdrant_collection()
		await self._push_to_qdrant()
		await self._push_to_mongodb()
