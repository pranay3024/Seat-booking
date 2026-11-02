# SeatDesk — Singing Show seat booking (Flask)

An admin-only booking system for a single show (BookMyShow-style seat map).
The layout is taken from your floor plan: **Stalls A–R (743 seats)** and **Balcony S–W (258 seats)** — **1,001 seats** in 4 blocks per row.

**What it does**
- Admin login (single admin account set by environment variables)
- After login, the **Singing Show** seat map opens directly
- Interactive seat map with zoom and fit controls
- Choose **1–50 seats**; clicking an available seat selects that many consecutive available seats in its row
- Book with customer details (name, phone, email, city, notes) — no prices or payments
- Double-booking is impossible (database-level lock on each seat)
- Click any grey (booked) seat to open that booking
- Printable ticket page, edit customer details, cancel booking (releases seats)
- Bookings list with search, filter by status, **CSV export** (opens in Excel)
- Works on phone and desktop

---

## Project structure

```
seatbook/
├── app.py              ← Flask app (all routes)
├── db.py               ← database helper (SQLite locally, Postgres in production)
├── seats.py            ← seat layout from the floor plan (edit here if a row is wrong)
├── requirements.txt
├── .python-version     ← tells Vercel to use Python 3.12
├── .env.example
├── templates/          ← HTML pages
└── public/static/      ← CSS, JS, icon (Vercel serves these from its CDN)
```

---

## Step 1 — Run it on your computer

You need **Python 3.10+** and **Git** installed.

```bash
cd seatbook
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac / Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

To use Supabase locally, put `DATABASE_URL` in the repository-root `.env` file
(next to the `seatbook` folder). The app loads it automatically; keep `.env`
private and URL-encode special characters in the database password (for example,
write `@` as `%40`). Leave `DATABASE_URL` unset to use local SQLite.

Open http://127.0.0.1:5000 and log in with **admin / admin123** (local default only).
Without `DATABASE_URL`, local data is saved in `seatdesk.db`.

> On Windows, if `psycopg2-binary` fails to install locally, run `pip install Flask` instead — you only need Postgres on Vercel.

---

## Step 2 — Push to GitHub

The repository is `https://github.com/pranay3024/Seat-booking`. From the repository root, push with:

```bash
git add seatbook
git commit -m "Add SeatDesk booking app"
git remote add origin https://github.com/pranay3024/Seat-booking.git
git push -u origin main
```

If `origin` is already configured, skip the `git remote add` command. `.gitignore` keeps local databases and `.env` files out of GitHub.

---

## Step 3 — Deploy on Vercel

1. Go to https://vercel.com → sign up / log in **with GitHub**.
2. **Add New… → Project** → find `seatdesk` → **Import**.
3. Set **Root Directory** to `seatbook`, then let Vercel detect **Flask**. Leave build settings as they are.
4. Open **Environment Variables** and add:

   | Name | Value |
   |---|---|
   | `ADMIN_USERNAME` | the login name you want, e.g. `admin` |
   | `ADMIN_PASSWORD` | a strong password |
   | `SECRET_KEY` | a long random string (see below) |
   | `APP_NAME` | *(optional)* e.g. `Rang Mandir Bookings` |

   Generate a SECRET_KEY:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
5. Click **Deploy**. You'll get a URL like `https://seatdesk.vercel.app`.

## Step 4 — Connect Supabase (important!)

Vercel's servers don't keep files, so bookings must go into a real database. The Supabase project URL alone is not a database connection string. In the Supabase dashboard for your project, open **Connect** and copy a PostgreSQL connection string (use the Supavisor transaction pooler if your host requires IPv4, such as Vercel).

In Vercel → your project → **Settings → Environment Variables**, set:

| Name | Value |
|---|---|
| `DATABASE_URL` | The full PostgreSQL URI copied from Supabase (including its password and SSL settings) |

Keep the connection string private. Do not put it in source code or commit it to GitHub. Set the other app secrets from Step 3 as environment variables too. Redeploy after saving the variables; the tables are created automatically when the app first connects.

The project URL for this app is `https://hezbwvzsbbdquxfvzfug.supabase.co`; it identifies the project but is not used as `DATABASE_URL`. The yellow warning banner disappears once the database connection is configured.

For local development, the app reads `DATABASE_URL` from the repository-root `.env`. Leave it unset to continue using the local SQLite database.

The database schema also creates an `admins` table with a `password_hash` column.
It is not populated automatically; the current login still uses
`ADMIN_USERNAME` and `ADMIN_PASSWORD` from the environment, and those values
should never be stored as plaintext in the database.

This project uses one fixed show, **Singing Show**. The first run creates it
if it does not exist. Show creation and selection are not available in the app.
To start with an empty seat map, remove the old shows and bookings from the
database, keeping only the intended Singing Show record.

## Step 5 — Making changes later

Edit the code, then:

```bash
git add .
git commit -m "Describe your change"
git push
```

Vercel redeploys automatically on every push to `main`.

---

## Customising

- **Seat layout** – `seats.py`. Each row is a list of 4 blocks `(first_seat, last_seat)`. Change numbers and everything (map, totals, validation) updates.
- **Max seats per booking** – `MAX_SEATS` in `app.py`.
- **Colours** – CSS variables at the top of `public/static/app.css` (`--accent` is the main colour).

## Troubleshooting

- **"ADMIN_PASSWORD is not set"** on login → add it in Vercel → Settings → Environment Variables, then redeploy.
- **Yellow "No database connected" banner** → set `DATABASE_URL` to the PostgreSQL connection URI from Supabase and redeploy.
- **500 error after adding the database** → check Vercel → your project → **Logs**. Confirm `DATABASE_URL` contains the full connection URI, including the correct password and SSL settings.
- **CSS not loading on Vercel** → make sure the `public/static` folder was pushed to GitHub.
