# System Health Endpoint

This endpoint is used to check the health status of the system. It can be used for monitoring purposes and to ensure that all components of the system are functioning correctly.

---

* **URL:** `/api/system/health`

* **Method:** `GET`

* **Authentication:** `None`

* **URL Parameters:**

> None

* **Request Body:**

> None

---

* **Successful Response:** Title

  * **Code:** `200`

  * **Response Object:**

        ```json
        {
            "meta": "<MetaData>",
            "data": null
        }
        ```

  * **Description:** Indicates that the system is healthy and all components are functioning correctly.

---

***Notes:*** This endpoint does not require authentication and can be used for monitoring purposes.
