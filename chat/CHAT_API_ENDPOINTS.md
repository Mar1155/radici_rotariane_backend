# Chat App - API Endpoints

Documentazione completa di tutti gli endpoint dell'applicazione Chat.

**Base URL**: `/api/chats/`

---

## 📋 Indice

- [Gestione Chat](#gestione-chat)
  - [Lista Chat](#1-lista-chat)
  - [Dettaglio Chat](#2-dettaglio-chat)
  - [Crea Chat Diretta](#3-crea-chat-diretta)
  - [Crea Gruppo](#4-crea-gruppo)
  - [Forum Globale](#45-forum-globale)
  - [Elimina Chat](#5-elimina-chat)
  - [Aggiorna Chat](#6-aggiorna-chat)
- [Gestione Partecipanti](#gestione-partecipanti)
  - [Aggiungi Partecipante](#7-aggiungi-partecipante)
  - [Rimuovi Partecipante](#8-rimuovi-partecipante)
  - [Esci dal Gruppo](#9-esci-dal-gruppo)
- [Gestione Messaggi](#gestione-messaggi)
  - [Lista Messaggi](#10-lista-messaggi)
  - [Invia Messaggio](#11-invia-messaggio)
  - [Dettaglio Messaggio](#12-dettaglio-messaggio)
  - [Elimina Messaggio](#13-elimina-messaggio)
  - [Aggiorna Messaggio](#14-aggiorna-messaggio)
  - [Traduci Messaggio](#15-traduci-messaggio)
- [WebSocket](#websocket)
  - [Connessione Chat](#16-connessione-websocket)

---

## Gestione Chat

### 1. Lista Chat

Recupera tutte le chat dell'utente autenticato (dirette e gruppi).

**Endpoint**: `GET /api/chats/`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Risposta** (200 OK):
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "chat_type": "direct",
    "name": null,
    "description": null,
    "created_by": 1,
    "created_at": "2025-11-02T10:30:00Z",
    "participants_details": [
      {
        "user_id": 1,
        "username": "user1",
        "role": "member",
        "joined_at": "2025-11-02T10:30:00Z"
      },
      {
        "user_id": 2,
        "username": "user2",
        "role": "member",
        "joined_at": "2025-11-02T10:30:00Z"
      }
    ],
    "participant_count": 2
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "chat_type": "group",
    "name": "Team Progetto",
    "description": "Chat per il team del progetto X",
    "created_by": 1,
    "created_at": "2025-11-02T11:00:00Z",
    "participants_details": [
      {
        "user_id": 1,
        "username": "user1",
        "role": "admin",
        "joined_at": "2025-11-02T11:00:00Z"
      },
      {
        "user_id": 3,
        "username": "user3",
        "role": "member",
        "joined_at": "2025-11-02T11:00:00Z"
      },
      {
        "user_id": 4,
        "username": "user4",
        "role": "member",
        "joined_at": "2025-11-02T11:00:00Z"
      }
    ],
    "participant_count": 3
  }
]
```

---

### 2. Dettaglio Chat

Recupera i dettagli di una chat specifica.

**Endpoint**: `GET /api/chats/{chat_id}/`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat

**Risposta** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "chat_type": "group",
  "name": "Team Progetto",
  "description": "Chat per il team del progetto X",
  "created_by": 1,
  "created_at": "2025-11-02T11:00:00Z",
  "participants_details": [
    {
      "user_id": 1,
      "username": "user1",
      "role": "admin",
      "joined_at": "2025-11-02T11:00:00Z"
    },
    {
      "user_id": 3,
      "username": "user3",
      "role": "member",
      "joined_at": "2025-11-02T11:00:00Z"
    }
  ],
  "participant_count": 2
}
```

**Errori**:
- `404 Not Found`: Chat non trovata o l'utente non è partecipante

---

### 3. Crea Chat Diretta

Crea o recupera una chat diretta (1-a-1) con un altro utente.

**Endpoint**: `POST /api/chats/direct/`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Body**:
```json
{
  "user_id": 2
}
```

**Risposta** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "chat_type": "direct",
  "name": null,
  "description": null,
  "created_by": 1,
  "created_at": "2025-11-02T10:30:00Z",
  "participants_details": [
    {
      "user_id": 1,
      "username": "user1",
      "role": "member",
      "joined_at": "2025-11-02T10:30:00Z"
    },
    {
      "user_id": 2,
      "username": "user2",
      "role": "member",
      "joined_at": "2025-11-02T10:30:00Z"
    }
  ],
  "participant_count": 2
}
```

**Note**:
- Se la chat diretta esiste già, viene restituita quella esistente
- Entrambi gli utenti vengono aggiunti come `member` (nessun admin nelle chat dirette)

**Errori**:
- `404 Not Found`: User ID non trovato

---

### 4. Crea Gruppo

Crea una nuova chat di gruppo.

**Endpoint**: `POST /api/chats/create_group/`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Body**:
```json
{
  "name": "Team Progetto",
  "description": "Chat per il team del progetto X",
  "participant_ids": [2, 3, 4]
}
```

**Parametri Body**:
- `name` (string, **required**): Nome del gruppo
- `description` (string, optional): Descrizione del gruppo
- `participant_ids` (array of integers, optional): Lista di User IDs da aggiungere al gruppo

**Risposta** (201 Created):
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "chat_type": "group",
  "name": "Team Progetto",
  "description": "Chat per il team del progetto X",
  "created_by": 1,
  "created_at": "2025-11-02T11:00:00Z",
  "participants_details": [
    {
      "user_id": 1,
      "username": "user1",
      "role": "admin",
      "joined_at": "2025-11-02T11:00:00Z"
    },
    {
      "user_id": 2,
      "username": "user2",
      "role": "member",
      "joined_at": "2025-11-02T11:00:00Z"
    },
    {
      "user_id": 3,
      "username": "user3",
      "role": "member",
      "joined_at": "2025-11-02T11:00:00Z"
    }
  ],
  "participant_count": 3
}
```

**Note**:
- Il creatore diventa automaticamente `admin`
- Gli altri partecipanti vengono aggiunti come `member`

**Errori**:
- `400 Bad Request`: Nome vuoto o participant_ids non validi

---

### 4.5 Forum Globale

Recupera (o crea se non esiste) il forum globale accessibile a tutti.

**Endpoint**: `GET /api/chats/forum/`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Risposta** (200 OK):
```json
{
  "id": "...",
  "chat_type": "forum",
  "name": "Forum Globale",
  "description": "Chat comune a tutti gli utenti",
  "created_by": null,
  "created_at": "...",
  "participants_details": [],
  "participant_count": 0
}
```

**Note**:
- Il forum è accessibile a tutti gli utenti autenticati.
- Non richiede di essere aggiunto come partecipante.

---

### 5. Elimina Chat

Elimina una chat (solo se l'utente ne è il creatore).

**Endpoint**: `DELETE /api/chats/{chat_id}/`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat

**Risposta** (204 No Content)

**Errori**:
- `403 Forbidden`: L'utente non è autorizzato a eliminare la chat
- `404 Not Found`: Chat non trovata

---

### 6. Aggiorna Chat

Aggiorna parzialmente i dettagli di una chat (nome, descrizione).

**Endpoint**: `PATCH /api/chats/{chat_id}/`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat

**Body**:
```json
{
  "name": "Nuovo Nome Gruppo",
  "description": "Nuova descrizione"
}
```

**Risposta** (200 OK):
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "chat_type": "group",
  "name": "Nuovo Nome Gruppo",
  "description": "Nuova descrizione",
  "created_by": 1,
  "created_at": "2025-11-02T11:00:00Z",
  "participants_details": [...],
  "participant_count": 3
}
```

---

## Gestione Partecipanti

### 7. Aggiungi Partecipante

Aggiunge un nuovo partecipante a una chat di gruppo (solo admin).

**Endpoint**: `POST /api/chats/{chat_id}/add_participant/`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat di gruppo

**Body**:
```json
{
  "user_id": 5
}
```

**Risposta** (200 OK):
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "chat_type": "group",
  "name": "Team Progetto",
  "description": "Chat per il team del progetto X",
  "created_by": 1,
  "created_at": "2025-11-02T11:00:00Z",
  "participants_details": [
    {
      "user_id": 1,
      "username": "user1",
      "role": "admin",
      "joined_at": "2025-11-02T11:00:00Z"
    },
    {
      "user_id": 5,
      "username": "user5",
      "role": "member",
      "joined_at": "2025-11-02T12:00:00Z"
    }
  ],
  "participant_count": 4
}
```

**Errori**:
- `400 Bad Request`: 
  - Non è una chat di gruppo
  - User ID non fornito
  - Utente già nel gruppo
- `403 Forbidden`: L'utente non è admin
- `404 Not Found`: User ID non trovato

---

### 8. Rimuovi Partecipante

Rimuove un partecipante da una chat di gruppo (solo admin).

**Endpoint**: `POST /api/chats/{chat_id}/remove_participant/`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat di gruppo

**Body**:
```json
{
  "user_id": 5
}
```

**Risposta** (200 OK):
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "chat_type": "group",
  "name": "Team Progetto",
  "description": "Chat per il team del progetto X",
  "created_by": 1,
  "created_at": "2025-11-02T11:00:00Z",
  "participants_details": [
    {
      "user_id": 1,
      "username": "user1",
      "role": "admin",
      "joined_at": "2025-11-02T11:00:00Z"
    }
  ],
  "participant_count": 3
}
```

**Errori**:
- `400 Bad Request`: 
  - Non è una chat di gruppo
  - User ID non fornito
  - Utente non nel gruppo
- `403 Forbidden`: L'utente non è admin

---

### 9. Esci dal Gruppo

Permette all'utente corrente di uscire da una chat di gruppo.

**Endpoint**: `POST /api/chats/{chat_id}/leave_group/`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat di gruppo

**Risposta** (200 OK):
```json
{
  "message": "Sei uscito dal gruppo."
}
```

**Oppure** (se ultimo partecipante):
```json
{
  "message": "Gruppo eliminato (ultimo partecipante uscito)."
}
```

**Note**:
- Se l'utente è l'ultimo partecipante, il gruppo viene automaticamente eliminato

**Errori**:
- `400 Bad Request`: 
  - Non è una chat di gruppo
  - Utente non è nel gruppo

---

## Gestione Messaggi

### 10. Lista Messaggi

Recupera gli ultimi messaggi di una chat (ultimi 50).

**Endpoint**: `GET /api/chats/{chat_id}/messages/`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat

**Risposta** (200 OK):
```json
[
  {
    "id": 1,
    "chat": "550e8400-e29b-41d4-a716-446655440000",
    "sender": 1,
    "sender_username": "user1",
    "body": "Ciao a tutti!",
    "created_at": "2025-11-02T10:35:00Z",
    "client_msg_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"
  },
  {
    "id": 2,
    "chat": "550e8400-e29b-41d4-a716-446655440000",
    "sender": 2,
    "sender_username": "user2",
    "body": "Ciao! Come va?",
    "created_at": "2025-11-02T10:36:00Z",
    "client_msg_id": "b2c3d4e5-f6a7-5b6c-9d0e-1f2a3b4c5d6e"
  }
]
```

**Note**:
- I messaggi sono ordinati dal più recente al più vecchio (limite 50)

---

### 11. Invia Messaggio

Invia un nuovo messaggio in una chat.

**Endpoint**: `POST /api/chats/{chat_id}/messages/`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat

**Body**:
```json
{
  "body": "Questo è un nuovo messaggio"
}
```

**Risposta** (201 Created):
```json
{
  "id": 3,
  "chat": "550e8400-e29b-41d4-a716-446655440000",
  "sender": 1,
  "sender_username": "user1",
  "body": "Questo è un nuovo messaggio",
  "created_at": "2025-11-02T10:37:00Z",
  "client_msg_id": "c3d4e5f6-a7b8-6c7d-0e1f-2a3b4c5d6e7f"
}
```

**Note**:
- Il `sender` viene automaticamente impostato sull'utente autenticato
- Il `client_msg_id` viene generato automaticamente

---

### 12. Dettaglio Messaggio

Recupera un messaggio specifico.

**Endpoint**: `GET /api/chats/{chat_id}/messages/{message_id}/`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat
- `message_id` (integer): ID del messaggio

**Risposta** (200 OK):
```json
{
  "id": 1,
  "chat": "550e8400-e29b-41d4-a716-446655440000",
  "sender": 1,
  "sender_username": "user1",
  "body": "Ciao a tutti!",
  "created_at": "2025-11-02T10:35:00Z",
  "client_msg_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"
}
```

---

### 13. Elimina Messaggio

Elimina un messaggio (solo il mittente può eliminare il proprio messaggio).

**Endpoint**: `DELETE /api/chats/{chat_id}/messages/{message_id}/`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat
- `message_id` (integer): ID del messaggio

**Risposta** (204 No Content)

**Errori**:
- `403 Forbidden`: L'utente non è il mittente del messaggio
- `404 Not Found`: Messaggio non trovato

---

### 14. Aggiorna Messaggio

Aggiorna parzialmente un messaggio (solo il mittente può modificare il proprio messaggio).

**Endpoint**: `PATCH /api/chats/{chat_id}/messages/{message_id}/`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Parametri URL**:
- `chat_id` (UUID): ID della chat
- `message_id` (integer): ID del messaggio

**Body**:
```json
{
  "body": "Messaggio modificato"
}
```

**Risposta** (200 OK):
```json
{
  "id": 1,
  "chat": "550e8400-e29b-41d4-a716-446655440000",
  "sender": 1,
  "sender_username": "user1",
  "body": "Messaggio modificato",
  "created_at": "2025-11-02T10:35:00Z",
  "client_msg_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"
}
```

**Errori**:
- `403 Forbidden`: L'utente non è il mittente del messaggio

---

### 15. Traduci Messaggio

Traduce il testo di un messaggio in una lingua supportata con caching automatico.

**Endpoint**: `POST /api/chats/{chat_id}/messages/{message_id}/translate/`

**Headers**:
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Body**:
```json
{
  "target_language": "en"
}
```

**Risposte**:
- `201 Created`: la traduzione è stata generata e salvata
- `200 OK`: la traduzione era già in cache e viene restituita immediatamente

**Esempio (201 Created)**:
```json
{
  "id": 42,
  "message": 5,
  "target_language": "en",
  "translated_text": "Hello everyone!",
  "provider": "deepl",
  "detected_source_language": "it",
  "created_at": "2025-11-02T10:40:00Z"
}
```

**Note**:
- La traduzione viene salvata per ciascuna coppia messaggio/lingua per evitare chiamate ripetute al provider.
- Le lingue disponibili si configurano tramite `TRANSLATION_SUPPORTED_LANGUAGES` (default: it, en, es, fr, de).
- Se un altro messaggio ha lo stesso testo, viene riutilizzata la traduzione già presente in cache senza chiamare il provider.

**Errori**:
- `400 Bad Request`: lingua non supportata o messaggio vuoto
- `403 Forbidden`: l'utente non partecipa alla chat
- `502 Bad Gateway`: il provider di traduzione ha restituito un errore
- `503 Service Unavailable`: nessun provider configurato

---

## WebSocket

### 16. Connessione WebSocket

Connessione WebSocket in tempo reale per ricevere e inviare messaggi.

**Endpoint**: `ws://your-domain/ws/chat/{chat_id}/?token={access_token}`

**Parametri URL**:
- `chat_id` (UUID): ID della chat
- `token` (query param): Access token JWT

**Esempio Connessione**:
```javascript
const ws = new WebSocket(
  'ws://localhost:8000/ws/chat/550e8400-e29b-41d4-a716-446655440000/?token=eyJ0eXAiOiJKV1QiLCJhbGc...'
);
```

#### Eventi in Entrata (dal Server)

**1. History (al momento della connessione)**
```json
{
  "type": "history",
  "data": [
    {
      "id": 1,
      "sender_id": 1,
      "body": "Messaggio 1",
      "created_at": "2025-11-02T10:35:00Z"
    },
    {
      "id": 2,
      "sender_id": 2,
      "body": "Messaggio 2",
      "created_at": "2025-11-02T10:36:00Z"
    }
  ]
}
```

**2. Nuovo Messaggio**
```json
{
  "type": "message",
  "data": {
    "id": 3,
    "sender_id": 1,
    "body": "Nuovo messaggio",
    "created_at": "2025-11-02T10:37:00Z"
  }
}
```

#### Eventi in Uscita (al Server)

**Invia Messaggio**
```json
{
  "type": "message.send",
  "body": "Ciao a tutti!"
}
```

#### Codici di Chiusura

- `4401`: Non autenticato (token mancante o non valido)
- `4403`: Non autorizzato (l'utente non è partecipante della chat)

**Esempio Completo JavaScript**:
```javascript
const chatId = '550e8400-e29b-41d4-a716-446655440000';
const token = 'eyJ0eXAiOiJKV1QiLCJhbGc...';

const ws = new WebSocket(`ws://localhost:8000/ws/chat/${chatId}/?token=${token}`);

// Connessione aperta
ws.onopen = () => {
  console.log('Connesso alla chat');
};

// Ricevi messaggi
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'history') {
    console.log('Storia messaggi:', data.data);
  } else if (data.type === 'message') {
    console.log('Nuovo messaggio:', data.data);
  }
};

// Invia messaggio
function sendMessage(text) {
  ws.send(JSON.stringify({
    type: 'message.send',
    body: text
  }));
}

// Errori
ws.onerror = (error) => {
  console.error('Errore WebSocket:', error);
};

// Chiusura
ws.onclose = (event) => {
  console.log('WebSocket chiuso:', event.code);
  if (event.code === 4401) {
    console.log('Non autenticato');
  } else if (event.code === 4403) {
    console.log('Non autorizzato');
  }
};
```

---

## Note Generali

### Autenticazione

Tutti gli endpoint (tranne WebSocket che usa token in query param) richiedono un token JWT nell'header:
```
Authorization: Bearer {access_token}
```

### Tipi di Chat

- **`direct`**: Chat diretta (1-a-1), esattamente 2 partecipanti, entrambi con ruolo `member`
- **`group`**: Chat di gruppo (3+ partecipanti), con admin e membri

### Ruoli Partecipanti

- **`admin`**: Può aggiungere/rimuovere partecipanti, modificare il gruppo
- **`member`**: Può solo inviare messaggi e uscire dal gruppo

### Permessi

- **Chat dirette**: Non si possono aggiungere/rimuovere partecipanti
- **Chat di gruppo**: Solo gli admin possono gestire i partecipanti
- **Messaggi**: Solo il mittente può modificare/eliminare i propri messaggi

### Limiti

- Lista messaggi: massimo 50 messaggi (dal più recente)
- History WebSocket: massimo 50 messaggi (dal più vecchio al più recente)
