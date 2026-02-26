# Mwalika Agent: Websocket Chat Endpoint

This endpoint is responsible for handling real-time chat interactions between the user and the agent. It uses WebSockets to enable bidirectional communication, allowing for a seamless and interactive chat experience. This endpoint manages the chat session, processes user messages, generates agent responses, and maintains the chat history and session state.

---

* **URL:** `/api/agent/ws/chat?access_token={access_token}`

* **Method:** `WEBSOCKET`

* **Authentication:** `URL Query Parameter`

    The request must include the `access_token` query parameter with the access token
    to authenticate the handshake request for establishing the WebSocket connection.

* **URL Parameters:**

  * `access_token` (string, required): The access token for authenticating the WebSocket connection. This token must be included as a query parameter in the WebSocket URL.

* **Request Body:**

    > None

---

* **Successful Response:** Websocket messages exchanged between user and agent

  * **Response Object:**

        ```json
        {
            "meta": "<MetaData>",
            "message": "<WebSocketMessage>"
        }
        ```

  * **Description:** Indicates that the WebSocket connection has been successfully established and messages are being exchanged between the user and the agent. The `message` field will contain the WebSocket messages sent by either the user or the agent, which can include user inputs, agent responses, and system notifications.

---

***Notes:*** This endpoint requires the `access_token` query parameter for authentication.
