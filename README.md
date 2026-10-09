# Robyn's Reading Room — book library app

**Testing build: v1.0.1**

A responsive static web app for tracking books, reading status, five-star ratings, personal notes and synopses. Title/author search uses Open Library. Remembered plot/character searches also query Google Books and combine catalogue matches; availability and ranking depend on the catalogues, so this is keyword-based discovery rather than guaranteed semantic search. When available, the Google Books description is saved as the book synopsis. Export your collection as JSON.

## Try it

Open `index.html` in a browser or publish the folder through GitHub Pages. Until cloud credentials are configured, the app works in **local preview mode** and keeps entries in that browser's `localStorage`. That mode is not a backup, is not shared between devices, and is not suitable for a public multi-user launch.

## Enable accounts and cloud storage (Supabase)

1. Create a Supabase project at [supabase.com](https://supabase.com/).
2. In **SQL Editor**, run all of `supabase-setup.sql`. This creates the books table and row-level security policies so users can access only rows whose `user_id` matches their account.
3. In Supabase **Authentication → URL Configuration**, set your Site URL to the deployed GitHub Pages address (for example `https://YOURNAME.github.io/robyns-reading-room/`) and add that URL under Redirect URLs. In **Authentication → Providers → Email**, enable the setting that requires email confirmation. Email confirmation is required by this app; users must confirm before they can sign in.
4. In **Project Settings → API**, copy the Project URL and the **anon/public** key. These are intended for browser use when row-level security is enabled. Never use the `service_role` key in this site.
5. Edit the `CONFIG` values near the start of `app.js`:

   ```js
   const CONFIG={url:'https://YOUR_PROJECT.supabase.co',key:'YOUR_ANON_PUBLIC_KEY'};
   ```

6. The app uses `t_humphreeze@hotmail.com` for support, privacy questions, and account-deletion requests. Change `SUPPORT_EMAIL` in `app.js` if that address changes.
7. Test signup, email confirmation, sign-in, add/edit/delete, sign-out, and a second account. Check that account two cannot see account one's books.
8. Commit the app files to a GitHub repository. Choose **Settings → Pages → Deploy from a branch**, select `main` and `/ (root)`, then save. The site will be available at the Pages URL. If the repository is private, confirm your GitHub plan supports Pages for that repository.

Do not commit private credentials. The Supabase anon/public key is visible to visitors by design; access protection comes from the database's RLS policies. Keep RLS enabled and never put a service-role key in browser code.

## If the confirmation link shows a 404

For a GitHub Pages project site, the URL normally includes the repository path, for example `https://USERNAME.github.io/REPOSITORY/`. In Supabase **Authentication → URL Configuration**:

- Set **Site URL** to that complete URL, including the repository path and trailing slash.
- Add the same complete URL under **Redirect URLs**.
- Do not use only `https://USERNAME.github.io` unless the repository is the account's special `USERNAME.github.io` user-site repository.

The app now sends the current GitHub Pages folder as `emailRedirectTo` for new sign-ups. After changing the Supabase settings, create a fresh test account or request a new confirmation email. An older link may still contain the old, incorrect redirect. If the old link displayed a 404 but the account was confirmed, return to the app and try signing in.

## Privacy, durability, and maintenance

- This is intended as a public signup site with private per-user book records. Users choose their own email/password; enable email confirmation and configure password/security options in Supabase.
- Use Supabase's backup options appropriate to your plan and periodically test restoring data. Backups are not the same as an export; users can download their own JSON via **Export my library**.
- The app relies on Open Library for catalogue search and cover art. Search quality, plot-description availability, synopses, and images are not guaranteed. The remembered-book feature searches catalogue fields and is not an AI semantic-search engine.
- The app includes an in-app privacy notice, support link, and account/data deletion process. Review the wording against your actual data practices and decide who will process deletion requests. Account deletion should be performed through Supabase's dashboard or a protected server-side/Edge Function process; never put a `service_role` key in browser code. Review Supabase's current terms and data-region options, and don't collect data you don't need.
- Current local-preview storage is unencrypted browser storage. Avoid adding sensitive personal information to notes in that mode.

## Remaining actions before public launch

The app is ready for a local preview. Complete this checklist before inviting public users:

- [ ] Create the Supabase project, run `supabase-setup.sql`, and add the project URL plus anon key to `app.js`.
- [ ] Configure Supabase Auth Site URL and Redirect URLs for the final GitHub Pages address, and enable required email confirmation in the Email provider settings.
- [ ] Deploy to GitHub Pages and test the real URL on a desktop, iPhone, and Android phone.
- [ ] Test the complete flow with two separate accounts: sign up, sign in, add, edit, rate, move between statuses, remove, sign out, and sign back in on another device.
- [ ] Confirm account isolation and RLS in Supabase: account B must never see account A's books.
- [ ] Test the export download and keep a backup before importing or migrating any existing library data.
- [ ] Review the in-app privacy notice, publish the support/contact method, and confirm who will process account/data deletion requests.
- [ ] Decide on a backup schedule and verify that a Supabase restore/export can be recovered.
- [ ] Optionally add a custom domain, favicon, analytics policy, and stronger account protections such as MFA if the public launch needs them.

Known catalogue limitation: synopsis, character, cover, and remembered-book results depend on Open Library and Google Books data. The memory search is keyword-based catalogue discovery, not guaranteed AI semantic search.

## Files

- `index.html`, `styles.css`, `app.js` — static app
- `supabase-setup.sql` — database table and per-user access rules
