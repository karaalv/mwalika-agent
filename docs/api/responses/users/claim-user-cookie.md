# Mwalika Claim User Cookie Endpoint

This endpoint is responsible for claiming the user cookie for an anonymous user. This is used to transition an anonymous user to an assigned user by claiming a generated user id and associating it with the client's session. This endpoint also generates a new refresh token to be stored as a client cookie which will be used to generate access tokens for the user to access the agent and also to track the user's usage for security and analytics purposes. A new access token is also generated and sent in the response body for the client to use in the `Authorization` header for subsequent requests.

---

* **URL:** `/api/users/claim-user-cookie`

* **Method:** `POST`

* **Authentication:** `HEADER`

    The request must include the `Authorization` header with the access token
    to authenticate the request.

* **URL Parameters:**

    > None

* **Request Body:**

    ```json
    {
        "user_id": "<string>",
        "claim_token": "<string>"
    }
    ```

---

* **Successful Response:** User Cookie Claimed and Refresh Token Set

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

  * **Description:** Indicates that the user cookie has been successfully claimed and the refresh token cookie has been set for the user.

---

***Notes:*** The request must come with a valid access token in the `Authorization` header to authenticate the request. The `user_id` and `claim_token` in the request body must match a valid claim token that was generated for an anonymous user. Upon successful claiming of the user cookie, the anonymous user will be transitioned to an assigned user with the specified `user_id`, and a new refresh token will be set as a cookie for the client to use for generating access tokens in the future. A new access token will also be included in the response body for the client to use in the `Authorization` header for subsequent requests.
