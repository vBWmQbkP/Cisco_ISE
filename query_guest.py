#!/usr/bin/env python3
"""
ISE Guest Query — look up guest accounts and their passwords
=============================================================
Queries ISE ERS API for guest users. The GET API returns the
password in guestInfo.password (works for both manually-set
and ISE auto-generated passwords).

Usage:
  python query_guest.py user1                       # by username
  python query_guest.py user1 user2 user3           # multiple
  python query_guest.py --email a@example.com       # by email
  python query_guest.py --file users.csv            # batch from CSV
  python query_guest.py --all                       # list all guests
"""

import argparse
import csv
import os
import sys

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _env(key: str, default: str = "") -> str:
    val = os.getenv(key, default)
    if val and len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
        val = val[1:-1]
    return val


# ── API ────────────────────────────────────────────────────

class GuestQuery:
    def __init__(self, host, user, pw):
        self.base = f"https://{host}:9060/ers/config/guestuser"
        self.auth = (user, pw)
        self.s = requests.Session()
        self.s.verify = False

    def _get(self, url: str):
        r = self.s.get(url, auth=self.auth, headers={"Accept": "application/json"}, timeout=15)
        return r

    def by_name(self, name: str) -> dict:
        """Look up one guest by username."""
        r = self._get(f"{self.base}/name/{name}")
        if r.status_code == 404:
            return {"status": "not_found", "name": name}
        if r.status_code != 200:
            return {"status": "error", "name": name, "error": f"HTTP {r.status_code}"}
        gu = r.json().get("GuestUser", {})
        return self._format(gu)

    def by_email(self, email: str) -> list:
        """Look up guests by email (email is inside guestInfo, so we scan all)."""
        results = []
        for gu in self.all():
            gi = gu.get("guestInfo", {})
            if gi.get("emailAddress", "").lower() == email.lower():
                results.append(self._format(gu))
        return results

    def all(self) -> list:
        """List all guest users (paginated)."""
        out = []
        page = 1
        while True:
            r = self._get(f"{self.base}?size=100&page={page}")
            if r.status_code != 200:
                break
            data = r.json()
            resources = data.get("SearchResult", {}).get("resources", [])
            for res in resources:
                # resources only have id+name; fetch full detail
                detail = self._get(res["link"]["href"] if "link" in res else f"{self.base}/{res['id']}")
                if detail.status_code == 200:
                    out.append(detail.json().get("GuestUser", {}))
            if len(resources) < 100:
                break
            page += 1
        return out

    @staticmethod
    def _format(gu: dict) -> dict:
        gi = gu.get("guestInfo", {})
        gai = gu.get("guestAccessInfo", {})
        return {
            "status": "found",
            "id": gu.get("id", ""),
            "name": gu.get("name", ""),
            "username": gi.get("userName", ""),
            "password": gi.get("password", ""),
            "firstName": gi.get("firstName", ""),
            "lastName": gi.get("lastName", ""),
            "email": gi.get("emailAddress", ""),
            "phoneNumber": gi.get("phoneNumber", ""),
            "company": gi.get("company", ""),
            "guestType": gu.get("guestType", ""),
            "accountStatus": gu.get("status", ""),
            "enabled": gi.get("enabled", ""),
            "validDays": gai.get("validDays", ""),
            "fromDate": gai.get("fromDate", ""),
            "toDate": gai.get("toDate", ""),
            "location": gai.get("location", ""),
        }


# ── Output ────────────────────────────────────────────────

def print_table(rows: list):
    if not rows:
        print("No results.")
        return
    cols = ["status", "username", "password", "email", "firstName", "lastName",
            "guestType", "accountStatus", "toDate"]
    active = [c for c in cols if any(str(r.get(c, "")) for r in rows)]
    widths = {c: max(len(c), max((len(str(r.get(c, ""))) for r in rows), default=0)) + 2 for c in active}
    sep = "-" * sum(widths.values())
    print(f"\n{sep}\n{''.join(f'{c:{widths[c]}}' for c in active)}\n{sep}")
    for r in rows:
        print("".join(f"{str(r.get(c, '')):{widths[c]}}" for c in active))
    print(sep)
    print(f"Total: {len(rows)}")


def main():
    p = argparse.ArgumentParser(description="ISE Guest Query — look up accounts & passwords")
    p.add_argument("names", nargs="*", help="Usernames to look up")
    p.add_argument("--email", "-e", action="append", default=[], help="Look up by email")
    p.add_argument("--file", "-f", default=None, help="CSV file with userName or emailAddress column")
    p.add_argument("--all", action="store_true", help="List all guests")
    p.add_argument("--output", "-o", default=None, help="Save results to CSV")
    args = p.parse_args()

    host = _env("ISE_HOST")
    user = _env("ISE_ERS_ADMIN")
    pw = _env("ISE_ERS_PASSWORD")
    if not host:
        print("Missing ISE_HOST in .env")
        sys.exit(1)

    q = GuestQuery(host, user, pw)

    print(f"\n{'='*60}\n  ISE Guest Query  |  {host}\n{'='*60}")

    rows = []

    if args.all:
        print("\nFetching all guests (may take a moment)...")
        for gu in q.all():
            rows.append(q._format(gu))
    else:
        for name in args.names:
            print(f"\nLooking up: {name}")
            rows.append(q.by_name(name))

        for email in args.email:
            print(f"\nLooking up email: {email}")
            found = q.by_email(email)
            if not found:
                rows.append({"status": "not_found", "email": email})
            else:
                rows.extend(found)

        if args.file:
            with open(args.file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("userName", "").strip():
                        rows.append(q.by_name(row["userName"].strip()))
                    elif row.get("emailAddress", "").strip():
                        found = q.by_email(row["emailAddress"].strip())
                        rows.extend(found or [{"status": "not_found", "email": row["emailAddress"].strip()}])

    print_table(rows)

    if args.output:
        cols = ["status", "username", "password", "email", "firstName", "lastName",
                "guestType", "accountStatus", "validDays", "toDate", "error"]
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"\nSaved: {args.output}")


if __name__ == "__main__":
    main()
