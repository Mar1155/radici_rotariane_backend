# Forum API Endpoints

Base URL: `/api/forum/`

## Authentication
All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

---

## Posts

### List Posts
```
GET /api/forum/posts/
```
Returns paginated list of posts sorted by newest first.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 15, max: 50)

**Response:**
```json
{
  "count": 100,
  "next": "http://example.com/api/forum/posts/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "title": "Post title",
      "description": "Post content...",
      "author": {
        "id": 1,
        "username": "user1"
      },
      "comment_count": 5,
      "created_at": "2024-11-27T10:00:00Z",
      "updated_at": "2024-11-27T10:00:00Z"
    }
  ]
}
```

### Get Post Detail
```
GET /api/forum/posts/{post_id}/
```
Returns post with all comments.

**Response:**
```json
{
  "id": "uuid",
  "title": "Post title",
  "description": "Full post content...",
  "author": {
    "id": 1,
    "username": "user1"
  },
  "comment_count": 5,
  "comments": [
    {
      "id": "uuid",
      "post": "post_uuid",
      "parent_id": null,
      "author": {
        "id": 2,
        "username": "user2"
      },
      "text": "Comment text",
      "created_at": "2024-11-27T10:00:00Z",
      "updated_at": "2024-11-27T10:00:00Z",
      "replies": [
        {
          "id": "reply_uuid",
          "post": "post_uuid",
          "parent_id": "uuid",
          "author": {
            "id": 3,
            "username": "user3"
          },
          "text": "Reply text",
          "created_at": "2024-11-27T11:00:00Z",
          "updated_at": "2024-11-27T11:00:00Z"
        }
      ]
    }
  ],
  "created_at": "2024-11-27T10:00:00Z",
  "updated_at": "2024-11-27T10:00:00Z"
}
```

### Create Post
```
POST /api/forum/posts/
```
Creates a new post.

**Request Body:**
```json
{
  "title": "Post title",
  "description": "Post content..."
}
```

**Response:** Returns the created post object.

### Update Post
```
PATCH /api/forum/posts/{post_id}/
```
Updates an existing post. Only the author can update.

**Request Body:**
```json
{
  "title": "Updated title",
  "description": "Updated content"
}
```

### Delete Post
```
DELETE /api/forum/posts/{post_id}/
```
Deletes a post. Only the author can delete.

---

## Comments

### List Comments for Post
```
GET /api/forum/posts/{post_id}/comments/
```
Returns paginated list of comments for a specific post.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)

### Add Comment to Post
```
POST /api/forum/posts/{post_id}/comments/
```
Adds a comment to a post.

**Request Body:**
```json
{
  "text": "Comment text"
}
```

**Request Body (reply example):**
```json
{
  "text": "Comment text",
  "parent_id": "parent_comment_uuid" // Optional, only for replies
}
```

**Response:** Returns the created comment object, including `parent_id` and nested `replies` (always empty for new comments).

**Notes:**
- Replies are limited to one nesting level (you cannot reply to an existing reply).
- `parent_id` must belong to a comment of the same post.

### Update Comment
```
PATCH /api/forum/comments/{comment_id}/
```
Updates an existing comment. Only the author can update.

**Request Body:**
```json
{
  "text": "Updated comment text"
}
```

### Delete Comment
```
DELETE /api/forum/comments/{comment_id}/
```
Deletes a comment. Only the author can delete.

---

## Error Responses

### 400 Bad Request
```json
{
  "field_name": ["Error message"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "error": "You can only delete your own posts."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```
