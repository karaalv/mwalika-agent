# Mwalika Agent: Delete Chat Session Endpoint

This endpoint is responsible for deleting a chat session and all associated data, including chat history and session state. This is used to allow users to manage their chat sessions and to ensure that data is not retained longer than necessary for privacy and security reasons.

---

* **URL:** `/api/agent/session/{session_id}`

* **Method:** `DELETE`

* **Authentication:** `HEADER`

    The request must include the `Authorization` header with the access token
    to authenticate the request.

* **URL Parameters:**

  * `session_id` (string, required): The unique identifier of the chat session to be deleted.

* **Request Body:**

    > None

---

* **Successful Response:** Chat Session Deleted

  * **Code:** `200`

  * **Response Object:**

        ```json
        {
            "meta": "<MetaData>",
            "data": null
        }
        ```

  * **Description:** Indicates that the chat session has been successfully deleted.

---

***Notes:*** This endpoint requires the `Authorization` header for authentication.
