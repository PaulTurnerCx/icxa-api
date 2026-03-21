# ICxA Maturity Map API

FastAPI application for scoring companies against ICxA maturity map criteria.

## Endpoints

- `GET /`
- `GET /health`
- `POST /score-company`

## Example request

```json
{
  "company": "AECOM",
  "website": "https://aecom.com",
  "submission_id": "12345"
}
