# Mwalika Agent: Update Chat Session Name Endpoint

This endpoint allows users to update the name of an existing chat session. The chat session name is used for display purposes in the user interface, making it easier for users to identify and manage their chat sessions.

---

* **URL:** `/api/agent/session/{session_id}/update-name`

* **Method:** `PUT`

* **Authentication:** `HEADER`

    The request must include the `Authorization` header with the access token
    to authenticate the request.

* **URL Parameters:**

  * `session_id` (string, required): The unique identifier of the chat session to be updated.

* **Request Body:**

    ```json
    {
        "new_name": "New Chat Session Name"
    }
    ```

  * `new_name` (string, required): The new name for the chat session. This should be a non-empty string.
  * **Notes:** The `new_name` will be scrubbed to remove any leading or trailing whitespace and to ensure it is a valid string.

---

* **Successful Response:** Chat Session Name Updated

  * **Code:** `200`

  * **Response Object:**

    ```json
    {
        "meta": "<MetaData>",
        "data": null
    }
    ```

  * **Description:** Indicates that the chat session name has been successfully updated.

---

***Notes:*** This endpoint requires the `Authorization` header for authentication.
