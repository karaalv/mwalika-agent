# Mwalika Agent: Get Chat Session Endpoint

This endpoint is responsible for retrieving a chat session and all associated data, including chat history and session state. This is used to allow users to view their chat sessions and to ensure that data is accessible for ongoing interactions.

---

* **URL:** `/api/agent/session/{session_id}/memory`

* **Method:** `GET`

* **Authentication:** `HEADER`

    The request must include the `Authorization` header with the access token
    to authenticate the request.

* **URL Parameters:**

  * `session_id` (string, required): The unique identifier of the chat session to be retrieved.

* **Request Body:**

    > None

---

* **Successful Response:** Chat Session Retrieved

  * **Code:** `200`

  * **Response Object:**

        ```json
        {
            "meta": "<MetaData>",
            "data": "<list[AgentMemory]>"
        }
        ```

  * **Description:** Indicates that the chat session has been successfully retrieved.

---

***Notes:*** This endpoint requires the `Authorization` header for authentication.
