# User management

Operations on existing users — profile, password, MFA, social linking, attributes,
friends, search, ban, export. Most are client-side (`Authorization: Bearer <user_JWT>`)
unless explicitly noted server-side (`X-SERVER-AUTHORIZATION: <server_JWT>`).

All endpoints below are documented under the official Login API: <https://developers.xsolla.com/api/login>.
URL slugs are taken from the `operationId` of each operation in `xsolla-login@941da4eff` (`swagger/**/*.yaml`).
Verify request schemas via the Xsolla MCP (`search_xsolla_sources`) before calling.

## Profile

| Task | API call | Auth |
|------|----------|------|
| Get the signed-in user's details | [Get user details](https://developers.xsolla.com/api/login/operation/get-user-details) | Bearer |
| Update the signed-in user's details | [Update user details](https://developers.xsolla.com/api/login/operation/update-user-details) | Bearer |
| Get user email | [Get user email](https://developers.xsolla.com/api/login/operation/get-user-email) | Bearer |
| Get / update / delete phone number | [Get user phone number](https://developers.xsolla.com/api/login/operation/get-user-phone-number), [Update user phone number](https://developers.xsolla.com/api/login/operation/update-user-phone-number), [Delete user phone number](https://developers.xsolla.com/api/login/operation/delete-user-phone-number) | Bearer |
| Verify a new phone number | [Request to link phone number to user as new method of authorization](https://developers.xsolla.com/api/login/operation/link-phone-number) → [Confirmation of request to link phone number to user](https://developers.xsolla.com/api/login/operation/confirm-phone-number) | Bearer |
| Add username/email auth to a social-only account | [Add username/email auth to account](https://developers.xsolla.com/api/login/operation/add-username-email-auth-to-account) | Bearer |
| Upload / delete profile picture | [Upload user picture](https://developers.xsolla.com/api/login/operation/upload-user-picture), [Delete user picture](https://developers.xsolla.com/api/login/operation/delete-user-picture) | Bearer |
| Get links for social auth | [Get links for social auth](https://developers.xsolla.com/api/login/operation/get-links-for-social-auth) | Bearer |
| Check user age (compliance) | [Check user age](https://developers.xsolla.com/api/login/operation/check-users-age) | Bearer |

## Password reset

| Task | API call |
|------|----------|
| Send reset email | [Reset password](https://developers.xsolla.com/api/login/operation/reset-password) |
| Confirm new password | [Confirm password reset](https://developers.xsolla.com/api/login/operation/confirm-password-reset) |
| Server-side reset (PA / your server) | [Send the reset password email to the user from Publisher Account or Server](https://developers.xsolla.com/api/login/operation/reset-password-from-server) |

The Widget exposes both as built-in screens. Custom UIs implement the two calls and host
the confirmation page on a Callback URL registered in PA.

## Multi-factor authentication (MFA / 2FA)

Project-wide policy + per-user enrollment. The flow during sign-in is: user authenticates
→ if MFA enabled, server returns `MfaRequired` (with a challenge token) → client
collects the one-time code → resubmits the auth call with the code → JWT is issued.

| Task | API call |
|------|----------|
| Get project two-factor authentication settings | [Get project two-factor authentication settings](https://developers.xsolla.com/api/login/operation/get-project-two-factor-authentication-settings) |
| Update project two-factor authentication settings | [Update project two-factor authentication settings](https://developers.xsolla.com/api/login/operation/update-project-two-factor-authentication-settings) |
| Get user's two-factor authentication settings (server-side) | [Get user's two-factor authentication settings](https://developers.xsolla.com/api/login/operation/get-server-mfa) |
| Update user's two-factor authentication settings (server-side) | [Update user's two-factor authentication settings](https://developers.xsolla.com/api/login/operation/update-server-mfa) |

Supported factors: TOTP authenticator app (RFC 6238), SMS, email. Configure the
allowed factors in PA → **Security → MFA**, or via `Update project two-factor
authentication settings`.

## Social account linking (within a single Login project)

Letting a user attach Google, Facebook, Steam, … to their existing account.

| Task | API call |
|------|----------|
| Build the link URL (browser flow) | [Get URL to link social network to account](https://developers.xsolla.com/api/login/operation/get-url-to-link-social-network-to-account) |
| Trigger the link (callback) | [Link social network to account](https://developers.xsolla.com/api/login/operation/link-social-network-to-account) |
| List linked networks | [Get linked networks](https://developers.xsolla.com/api/login/operation/get-linked-networks) |
| Unlink a network | [Delete linked network](https://developers.xsolla.com/api/login/operation/delete-linked-networks) |

Notes:

- Linking is from a logged-in session — the user is signed in (Bearer JWT) and adds a
  new identity.
- A given social identity can be linked to at most **one** Xsolla user; collisions
  return `SocialAccountAlreadyLinked`.
- Unlinking is supported; linking the same provider twice replaces the previous link.

## Account linking across projects (main ↔ shadow / cross-platform)

Used in the cross-platform model — the platform account in a shadow project gets linked
to the main account in a standard project.

| Task | API call |
|------|----------|
| Generate a one-time code on the source account | [Create code for linking accounts](https://developers.xsolla.com/api/login/operation/create-code-for-linking-accounts) |
| Consume the code on the target account | [Link accounts by code](https://developers.xsolla.com/api/login/operation/link-accounts-by-code) (server, requires server JWT) |
| Server-side direct link via external ID | [Link user IDs via external ID](https://developers.xsolla.com/api/login/operation/link-user-ids-via-external-id) |

Once linked, silent auth on the platform side returns the **main account's JWT** — no
duplication of progress, payments, or inventory.

## Attributes (per-user JSON)

Custom JSON keyed by `key`, used for save state, preferences, and partner-defined data.
Two flavors: writable by the client vs read-only (server-managed).

| Task | API call | Auth |
|------|----------|------|
| Read user's writable attributes | [Get user attributes from client](https://developers.xsolla.com/api/login/operation/get-users-attributes-from-client) | Bearer |
| Read user's read-only attributes | [Get read-only user attributes from client](https://developers.xsolla.com/api/login/operation/get-users-read-only-attributes-from-client) | Bearer |
| Update user's writable attributes | [Update user attributes from client](https://developers.xsolla.com/api/login/operation/update-users-attributes-from-client) | Bearer |
| Server: read writable attributes | [Get user attributes from server](https://developers.xsolla.com/api/login/operation/get-users-attributes-from-server) | Server |
| Server: read read-only attributes | [Get read-only user attributes from server](https://developers.xsolla.com/api/login/operation/get-users-read-only-attributes-from-server) | Server |
| Server: write attributes | [Update user attributes from server](https://developers.xsolla.com/api/login/operation/update-users-attributes-from-server) | Server |
| Server: write read-only attributes | [Update user read-only attributes from server](https://developers.xsolla.com/api/login/operation/update-users-read-only-attributes-from-server) | Server |
| Server: write attributes by server custom ID | [Update user attributes from server by server custom ID](https://developers.xsolla.com/api/login/operation/update-users-attributes-from-server-by-server-custom-id) | Server |
| Server: list users matching attribute filter | [Get users by attribute from server](https://developers.xsolla.com/api/login/operation/get-users-by-attribute-from-server) | Server |
| Get attributes by server custom IDs | [Get attributes by server custom IDs](https://developers.xsolla.com/api/login/operation/get-attributes-by-server-custom-id) | Server |
| Get attributes by user ID | [Get attributes by user ID](https://developers.xsolla.com/api/login/operation/get-attributes-by-user-id) | Server |
| Validation schema | [Get schema](https://developers.xsolla.com/api/login/operation/get-attributes-schema), [Update schema](https://developers.xsolla.com/api/login/operation/put-attributes-schema), [Delete schema](https://developers.xsolla.com/api/login/operation/delete-attributes-schema) | Server |

Use **read-only** attributes for anti-cheat-sensitive state (level, currency); the client
cannot tamper with them, only read. Use the **schema** endpoints to enforce shape — drops
the bug class of "client wrote a malformed JSON".

## Friends

| Task | API call |
|------|----------|
| Get user friends | [Get user friends](https://developers.xsolla.com/api/login/operation/get-users-friends) |
| Update user friends | [Update user friends](https://developers.xsolla.com/api/login/operation/update-users-friends) |
| Get social account friends | [Get social account friends](https://developers.xsolla.com/api/login/operation/get-social-account-friends) |
| Update social account friends | [Update social account friends](https://developers.xsolla.com/api/login/operation/update-social-account-friends) |

Friends list is independent of the platform-native friends list; "social account
friends" pulls the friends from the linked social network when the provider exposes them.

## Search

| Task | API call | Auth |
|------|----------|------|
| Search users (admin) | [Search users](https://developers.xsolla.com/api/login/operation/search-users-by-filter) | Server |
| Get user by ID for project | [Get user by ID for project](https://developers.xsolla.com/api/login/operation/get-user-for-project) | Server |
| Get user by ID | [Get user by ID](https://developers.xsolla.com/api/login/operation/get-user) | Server |
| Search users by nickname (client) | [Search users by nickname](https://developers.xsolla.com/api/login/operation/search-users-by-nickname) | Bearer |
| Get social profiles | [Get social profiles](https://developers.xsolla.com/api/login/operation/get-all-users-social-profiles) | Server |
| Resolve users by social ID + platform | [Get user IDs by social ID and platform](https://developers.xsolla.com/api/login/operation/get-users-ids-by-social-id-and-platform) | Server |

## Ban / unban

| Task | API call |
|------|----------|
| Ban user | [Ban user](https://developers.xsolla.com/api/login/operation/post-projects-users-ban) |
| Unban user | [Unban user](https://developers.xsolla.com/api/login/operation/del-projects-users-ban) |

A banned user's auth call returns `Forbidden` with a reason payload. Bans can be time-
limited or permanent.

## User groups

Logical groupings used for segmenting users (e.g. "early access", "QA"). Membership shows
in JWT `groups` claim — easy to gate features on.

| Task | API call |
|------|----------|
| Get / add / update / delete project groups | [Get project groups](https://developers.xsolla.com/api/login/operation/get-project-user-groups), [Add new group to project](https://developers.xsolla.com/api/login/operation/post-project-user-group), [Update group name](https://developers.xsolla.com/api/login/operation/put-project-user-group), [Delete group from project](https://developers.xsolla.com/api/login/operation/del-project-user-group) |
| Get / update / delete user groups | [Get user groups](https://developers.xsolla.com/api/login/operation/get-user-groups), [Update user groups](https://developers.xsolla.com/api/login/operation/update-user-groups), [Delete user groups](https://developers.xsolla.com/api/login/operation/delete-user-groups) |
| Manage groups for user | [Manage groups for user](https://developers.xsolla.com/api/login/operation/manage-user-groups) |

## Export / import

For migrations and GDPR DSAR responses.

| Task | API call |
|------|----------|
| Export user data | [Export user data](https://developers.xsolla.com/api/login/operation/export-users) |
| Import user data | [Import user data](https://developers.xsolla.com/api/login/operation/upload-import-file) |

Export is asynchronous — the call kicks off a job; the result is delivered to a download
URL or a configured S3 bucket. Import is bulk-only; for single-user creation use
`Register new user from server` ([`auth-flows.md`](auth-flows.md) §2).

## Custom email & SMS templates

For branded emails and locale-specific content.

| Task | API call |
|------|----------|
| Get custom email template | [Get custom email template](https://developers.xsolla.com/api/login/operation/get-custom-email-template) |
| Create custom email template | [Create custom email template](https://developers.xsolla.com/api/login/operation/create-custom-email-template) |
| Update custom email template | [Update custom email template](https://developers.xsolla.com/api/login/operation/update-custom-email-template) |
| Switch welcome email on / off | [Switch on welcome email](https://developers.xsolla.com/api/login/operation/switch-on-welcome-email), [Switch off welcome email](https://developers.xsolla.com/api/login/operation/switch-off-welcome-email) |
| Send email based on template | [Send email based on template](https://developers.xsolla.com/api/login/operation/send-email-based-on-template) |

SMS templates and the SMS provider ("Custom SMS provider" or Xsolla default) live under
**Communication providers** in PA; the consumer is `cmd/consumers/sms-consumer/` in the
`xsolla-login` repo.

## Webhooks (Login events)

Subscribe to user-lifecycle events (registered, signed in, banned, MFA, …):

| Task | API call |
|------|----------|
| Get webhooks for event | [Get webhooks for event](https://developers.xsolla.com/api/login/operation/get-webhooks-for-event) |
| Add webhook for event | [Add webhook for event](https://developers.xsolla.com/api/login/operation/add-webhook-for-event) |
| Delete webhook for event | [Delete webhook for event](https://developers.xsolla.com/api/login/operation/delete-webhook-for-event) |

Verification rules (raw body + secret + signature) follow the same family as Pay Station
/ Store webhooks — see the `webhooks-impl` skill for the handler shape.
