# Agent-side Login work through the Xsolla CLI

The agent's own Login operations: pick or create the Login project, read its settings,
make sandbox test users, and manage Login webhooks. Code the developer ships never calls
the CLI. It uses the Login API or an SDK ([`auth-flows.md`](auth-flows.md)).

Run the preflight in the parent [`SKILL.md`](../SKILL.md) first. Confirm flags with
`xsolla login <command> --help` before the first call, because they are not uniform: the
Login project ID is `--project-id` on most user commands, `--projectid` on `jwt-token`
and `--login-project-id` on the webhook commands.

With `--json`, success prints `{"ok":true,"data":…}` on stdout. A failure leaves stdout
empty and prints `{"ok":false,"error":…}` on stderr. Exit codes: `10` auth, `30`
validation, `40` not found. A missing required flag exits `1` with plain text on stderr.

## 1. Pick or create the Login project

`--publisher-id` is required on both commands, and they don't read it from config:

```bash
mid=$(xsolla config get merchant-id --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["value"])')
pid=$(xsolla config get project-id --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["value"])')
xsolla login list-project --publisher-id "$mid" --json \
  | python3 -c 'import json,sys; [print(p["id"], p["type"], p.get("publisher_project_id"), p["name"]) for p in json.load(sys.stdin)["data"]]'
```

Show the list and ask which project this game uses. A project whose
`publisher_project_id` matches `project_id` from config is the likely one. If none fits,
confirm a name and a type with the user, then dry-run:

```bash
xsolla login create-project --publisher-id "$mid" --publisher-project-id "$pid" \
  --name "<Game name>" --type master --dry-run --json     # prints the POST and body only
```

After a yes, run the same command without `--dry-run`; `data.id` is the new UUID.

- `--type master` is a standard (main-account) project. `--type shadow` is a
  platform-account project for one publishing platform; it requires
  `--publisher-project-id`. `create-project` has no flag that names the shadow
  project's main project, so check that link in Publisher Account.
- `--publisher-project-id` links the Login project to the game's publisher project. It
  appears as `publisher_project_id` in `list-project`.

Pin the chosen UUID to this game. Run it in the game's root, where `merchant-setup` put
`./.xsolla.json`:

```bash
[ -f .xsolla.json ] || echo "run merchant-setup Step 3 first: no ./.xsolla.json here"
xsolla config set login-project-id <uuid>
xsolla config get login-project-id --json     # data.value; "" means unset
```

Don't run `xsolla login setup`. It is an interactive wizard that prompts on stdin and
opens a browser, and its webhook step needs the server JWT from §4. Its hint to run
`xsolla login list-projects` names a command that doesn't exist; the command is
`list-project`. The user can run the wizard in their own terminal if they prefer it.

## 2. Read the project's settings

`list-project` returns the settings the agent needs to check the Publisher Account work:

```bash
lp=$(xsolla config get login-project-id --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["value"])')
xsolla login list-project --publisher-id "$mid" --json | python3 -c '
import json,sys
p = next(p for p in json.load(sys.stdin)["data"] if p["id"] == sys.argv[1])
for k in ("name","type","users_storage","login_urls","allowed_origins","email_confirmation_needed","token_expiration_time"):
    print(k, "=", p.get(k))' "$lp"
```

- `login_urls` are the Callback URLs, and `allowed_origins` is the CORS list. Each must
  contain the app's URL byte-for-byte.
- `email_confirmation_needed: true` means a new user must click the emailed link before
  password sign-in works.
- `token_expiration_time` is the user JWT lifetime in seconds.

There is no command to change these values. Send the user to Publisher Account
([`setup-pa.md`](setup-pa.md)), then read them again.

## 3. Sandbox test users

Login projects have no sandbox mode: a test user is a real account in the project's user
store, and no CLI command deletes it. Ask before creating one. Use an inbox the user
controls (a `+test` alias works), and a generated throwaway password, never a real one.
Keep the password in the git-ignored `.env`, never in the chat:

```bash
grep -q '^XSOLLA_LOGIN_TEST_PASSWORD=' .env \
  || printf 'XSOLLA_LOGIN_TEST_PASSWORD=%s\n' "$(python3 -c 'import secrets; print("Tst-" + secrets.token_urlsafe(18))')" >> .env
pw=$(sed -n 's/^XSOLLA_LOGIN_TEST_PASSWORD=//p' .env)
xsolla login register-jwt --project-id "$lp" --username "<test-username>" \
  --email "<test inbox>" --password "$pw" --json >/dev/null; echo "exit=$?"
unset pw
```

`register-jwt` takes the password only as a flag, and its `--dry-run` output prints it, so
skip the dry-run for this one command. A 400 with code `003-007` or "registration is
disabled" means sign-up is off: the user enables **Allow new user registration** under
Login → User database in Publisher Account.

When `email_confirmation_needed` is true, the user clicks the confirmation link. Then get
the test user's JWT and hand it straight to the developer's backend, in the same command:

```bash
pw=$(sed -n 's/^XSOLLA_LOGIN_TEST_PASSWORD=//p' .env)
jwt=$(printf '%s\n' "$pw" | xsolla login jwt-token --projectid "$lp" \
  --username "<test inbox>" --password-stdin -o text) && [ -n "$jwt" ] \
  && <request to the app's protected route with "Authorization: Bearer $jwt"; expect 200>
unset pw jwt
```

Then send a tampered copy of the token (one changed character in the signature) and
expect 401. Error `003-007` from `jwt-token` means the email isn't confirmed yet. Never
print the JWT, and never put it in `XSOLLA_TOKEN`: that overrides the CLI's publisher
sign-in.

Passwordless email (JWT protocol): `login start-email-jwt --project-id "$lp" --email
"<test inbox>" --json` returns `data.operation_id`, and the code goes to the inbox. The
user runs `login confirm-email-jwt --project-id … --email … --operation-id … --code …` in
their own terminal, so the one-time code never passes through the chat. The OAuth 2.0
variants (`start-email-oauth`, `confirm-email-oauth`) take `--client-id`: the numeric
OAuth client ID from `xsolla config get oauth-client-id`, not the Login project UUID.

The test password is the only test value this skill keeps in `.env`. Remove the
`XSOLLA_LOGIN_TEST_PASSWORD` line before the app's `.env` is used anywhere but local
development.

## 4. Login webhooks

Login webhooks are separate from Pay Station / Store webhooks. The commands authenticate
with a Login **server JWT** in `XSOLLA_LOGIN_SERVER_TOKEN`, not the CLI sign-in. Without
it they exit `1` with *"XSOLLA_LOGIN_SERVER_TOKEN is required"*, even with `--dry-run`.
The CLI has no way to fetch this token. The user copies it from **Publisher Account →
Login → your project → Security**, sets it in their own terminal, and runs the commands
there:

```bash
read -rs XSOLLA_LOGIN_SERVER_TOKEN && export XSOLLA_LOGIN_SERVER_TOKEN   # user's shell only
xsolla login add-webhook --login-project-id <uuid> --event-type registration \
  --url "https://<game backend>/xsolla/login-webhook" --json
xsolla login list-webhook --login-project-id <uuid> --event-type registration --json
xsolla login delete-webhook --login-project-id <uuid> --event-type registration \
  --webhook-id <id> --force
```

`--event-type` is one of `registration`, `authorization`, `email_confirmation`,
`link_social_account`, `new_verified_user`. The URL must be HTTPS. Never put the server
JWT in `.env`, a file or the chat. The alternative is the Login webhooks page in
Publisher Account. The handler code belongs to `webhooks-impl`.
