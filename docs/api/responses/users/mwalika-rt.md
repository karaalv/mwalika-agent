# Mwalika Refresh Token Endpoint

This endpoint is responsible for creating the general refresh token for an anonymous user (before being assigned a user id). This is used to generate an access token that can be used to access the agent and also to track the user's usage for security and analytics purposes.

---

* **URL:** `/api/users/mwalika-rt`

* **Method:** `GET`

* **Authentication:** `HEADER`

    The request must include the `X-Mwalika` header with the security token
    to authenticate the request.

* **URL Parameters:**

    > None

* **Request Body:**

    > None

---

* **Successful Response:** Refresh Token Cookie Set

  * **Code:** `200`

  * **Response Object:**

        ```json
        {
            "meta": "<MetaData>",
            "data": null
        }
        ```

  * **Description:** Indicates that the refresh token cookie has been successfully set for the anonymous user.

---

***Notes:*** This endpoint requires the `X-Mwalika` header for authentication.
