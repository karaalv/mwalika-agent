# Mwalika Agent: Get User Chat Sessions Endpoint

This endpoint is responsible for retrieving all chat sessions associated with a specific user. This allows users to view their chat history and manage their sessions effectively.

---

* **URL:** `/api/agent/sessions`

* **Method:** `GET`

* **Authentication:** `HEADER`

    The request must include the `Authorization` header with the access token
    to authenticate the request.

* **URL Parameters:**

    > None

* **Request Body:**

    > None

---

* **Successful Response:** User Chat Sessions Retrieved

  * **Code:** `200`

  * **Response Object:**

        ```json
        {
            "meta": "<MetaData>",
            "data": "<list[AgentSession]>"
        }
        ```

  * **Description:** Indicates that the user's chat sessions have been successfully retrieved.

---

***Notes:*** This endpoint requires the `Authorization` header for authentication. The `user_id` is derived from the access token provided in the `Authorization` header, and the endpoint will return all chat sessions associated with that user.
