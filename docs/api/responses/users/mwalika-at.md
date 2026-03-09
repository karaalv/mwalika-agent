# Mwalika Access Token Endpoint

This endpoint is responsible for creating the general access token for a user, note it works for both anonymous users (before being assigned a user id) and assigned users. This token is used to access the agent and also to track the user's usage for security and analytics purposes.

---

* **URL:** `/api/users/mwalika-at`

* **Method:** `GET`

* **Authentication:** `JWT`

    The request must include the `mwalika_rt` cookie with the refresh token
    to authenticate the request.

* **URL Parameters:**

    > None

* **Request Body:**

    > None

---

* **Successful Response:** Access Token sent

  * **Code:** `200`

  * **Response Object:**

        ```json
        {
            "meta": "<MetaData>",
            "data": {
                "access_token": "<JWT>",
                "expires_at_ms": "<int>"
            }
        }
        ```

  * **Description:** Indicates that the access token has been successfully generated for the user.

---

***Notes:*** This endpoint requires the `mwalika_rt` cookie for authentication. Note that the access token is intended to be used in the `Authorization` header for subsequent requests to access the agent and other protected resources. Therefore, it is not sent as a cookie but rather in the response body for the client to store and use as needed; this is to prevent CSRF attacks and to allow more flexible usage of the access token across different types of clients (e.g., web, mobile).
