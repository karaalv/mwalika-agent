# Mwalika User Path: Language Preference Update Endpoint

This endpoint allows authenticated users to update their language preference. The language preference is used to tailor the user experience, such as providing responses in the user's preferred language.

---

* **URL:** `/api/users/language-preference/{language}`

* **Method:** `PATCH`

* **Authentication:** `JWT`

    The request must include a valid access token in the `Authorization` header to authenticate the user.

* **URL Parameters:**

  * `language` (string): The new language preference to be set for the user. Valid options are defined in the `LanguagePreference` enum.

* **Request Body:**

    > None

---

* **Successful Response:** Language preference updated

  * **Code:** `200`

  * **Response Object:**

        ```json
        {
            "meta": "<MetaData>",
            "data": null
        }
        ```

  * **Description:** Indicates that the user's language preference has been successfully updated.

---

***Notes:*** The endpoint validates the provided language against a predefined set of valid options. If an invalid language is provided, the endpoint will return a `422 Validation Error` response with an appropriate error message. Note that the language preference is stored as part of the user's profile and may be used to customize the user experience across the application.
