# Mwalika User Path: Feedback Endpoint

This endpoint allows authenticated users to submit feedback about their experience with the Mwalika platform. The feedback can include comments, suggestions, or issues encountered while using the platform. The endpoint is designed to collect user feedback in a structured manner and store it for further analysis and improvement of the platform.

---

* **URL:** `/api/users/feedback`

* **Method:** `POST`

* **Authentication:** `JWT`

    The request must include a valid access token in the `Authorization` header to authenticate the user.

* **URL Parameters:**

    > None

* **Request Body:**

    ```json
    {
        "session_id": "<string>",
        "memory_id": "<string>",
        "language_preference": "<LanguagePreference>",
        "prompt_source": "<PromptSource>",
        "helpful": "<boolean>",
        "intended_service_category": "<IntendedServiceCategory>",
        "service_matched_quality": "<ServiceMatchedQuality>",
        "what_helped": "<WhatHelped[]>",
        "what_went_wrong": "<WhatWentWrong[]>",
        "comments": "<string>",
    }
    ```

---

* **Successful Response:** Feedback submitted

  * **Code:** `201`

  * **Response Object:**

    ```json
    {
        "meta": "<MetaData>",
        "data": null
    }
    ```

  * **Description:** Indicates that the user's feedback has been successfully submitted.

---

***Notes:*** The endpoint processes the feedback submitted by the user and stores it in the database. Additionally, it adds a record of the feedback to a Google Sheet for further analysis. Note that errors relating to updating the Google Sheet will not affect the successful submission of feedback, and the endpoint will still return a success response as long as the feedback is stored in the database. If the access token is invalid or expired, the endpoint will return an appropriate error response (e.g., `401 Unauthorized`).
