# Mwalika User Path: Self Endpoint

This endpoint allows authenticated users to retrieve their own user information, such as their user ID and language preference. It is designed to provide users with a way to access their profile information securely.

---

* **URL:** `/api/users/me`

* **Method:** `GET`

* **Authentication:** `JWT`

    The request must include a valid access token in the `Authorization` header to authenticate the user.

* **URL Parameters:**

    > None

* **Request Body:**

    > None

---

* **Successful Response:** User information retrieved

  * **Code:** `200`

  * **Response Object:**

        ```json
        {
            "meta": "<MetaData>",
            "data": "<AnonymousUser>"
        }
        ```

  * **Description:** Indicates that the user's information has been successfully retrieved.

---

***Notes:*** The endpoint retrieves the user's information based on the user ID encoded in the access token. If the access token is valid and corresponds to an existing user, the endpoint will return the user's information. If the token is invalid or expired, the endpoint will return an appropriate error response (e.g., `401 Unauthorized`). Note that this endpoint is intended for users to access their own information and does not allow retrieval of other users' information for security and privacy reasons.
