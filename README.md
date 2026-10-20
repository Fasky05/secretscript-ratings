# SecretScript provider ratings

Shared ratings of the free AI providers used through FreeLLMAPI in SecretScript.

- SecretScript reads `ratings.json` from this repo and lists the best providers first.
- Voting needs no account. SecretScript sends an anonymous vote to the SecretScript ratings worker (Cloudflare), which writes the totals here every 15 minutes, only when something changed.
- One vote per SecretScript install and provider. Voting again replaces the previous vote. Each internet connection can send at most 20 votes a day. Votes older than a year expire.
- A vote holds the stars (1-5) plus the success count, failure count and median reply time measured by the voter's own FreeLLMAPI. No keys, prompts, IP addresses or personal data are stored.

Score (0-100) = 60% stars (smoothed toward 3/5 until enough votes) + 30% success rate + 10% speed.
