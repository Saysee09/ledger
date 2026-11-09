## Ledger v8.9 · What's new

- **📥 Import old data** (Settings → Import old data): expenses from a CSV or rows pasted from Excel / Google Sheets (Date, Amount, Category, Account, Note), and **salary / income month by month** (Month, Amount). Template to download, preview before importing, duplicates skipped, old entries never disturb today's balances
- **💬 Send feedback** (Settings → Help us improve): idea, problem or like, with an optional reply email. It goes straight to the app maker's inbox
- **After an update**: Android closes the app while installing. Ledger now pops a notification **"✅ Ledger updated · tap to open"** the moment it's done, and says so when it opens

## From 8.8

- **Cleaner pages**:
  - **Expenses**: total, one "Free to spend" line, the bell line, search and your list. That's it
  - **Money → Accounts** (new first tab): every bank, cash, card and held-for-others tile, plus Net worth, Loans, Goals and Investments in one place
  - **Insights** has tabs: **Overview · Spending · Trends · Net worth**
- **📈 Investments, rebuilt** (Money → Invest): portfolio worth now vs invested, gain and **yearly return (XIRR)** overall and per holding, "Where it is" split by type, **🪙 gold by grams × today's rate**, and your **SIPs** with + Add SIP
- **✏️ Payee nicknames**: tap the payee name on any bank SMS (or in Settings → Bank SMS → what Ledger learned) and rename it, e.g. Roppen Transpor → Rapido. Shown everywhere, and search finds it
- **🔎 Smart search** on Expenses: `uber >200` · `food last month` · `100-300` · `5 nov` · `oct` · `#evol` · `under 50`
- **🧩 Free-to-spend widget** now also shows what you spent today
- **🔁 Repeat payments spotted** (Plan → Bills, and a heads-up in the bell): rent, subscriptions, recharges found from your history. **+ Remind** turns one into a reminder; ✕ hides it for good

## Also new in this build
- **Net worth follows the month you pick** on Insights: "Net worth on 30 Sept" for past months, plus how much it went up or down in that period
- **Big ₹ boxes** (Match balance, add expense, pay card…) show Indian commas as you type, e.g. 1,06,559.51, and the text shrinks so the whole number always fits
- 👆 **Fingerprint pops up by itself** when Ledger is locked (PIN / pattern stays underneath if you cancel). Switch: Settings → Lock & privacy
- **Ignore = "already logged"**: Ledger never learns from ignored SMS. Ignored SMS you already logged by hand, or whose payee you filed later, leave the list on their own
- **🗑 Delete** ignored SMS one by one or all at once (with Undo)
- **Page titles never get cut** ("Money moves"): buttons sit on the top line, the title has the full width below

## Cleaner pages
- **✨ button (top right)** opens a side panel with tabs: **Ask · Pulse · Wrap**. They are no longer cards on Expenses and Insights. Swipe right to close
- **Expenses search** only searches your expenses now (note, category, account, amount, payee). Ask lives in the ✨ panel

## Fixed
- **Typing in search / Ask**: the bottom bar hides while the keyboard is open and the box you type in moves into view
- **Net worth**: a credit card **limit** never counts as your money. Tap **Net worth** (Insights) to choose what counts. Default: banks + cash + investments. Optional: subtract card dues, include loans, leave out any account
- **Credit cards** now have a **Credit limit** and **You owe** field. A card whose limit was typed in as its balance is flagged ⚠️ with a one-tap fix. Home shows what's free on each card. Add as many cards as you like (Net worth → + Add a credit card)
- "Ignored" is never pre-filled from history, and "Ignore all" doesn't teach Ledger
- App updates: live versions are no longer labelled "test"

## You decide what Ledger learns (Settings → Bank SMS)
- **🚫 Ignored messages**: see them, tap one to file it, or **Put all back to sort**. **Stop learning** from them in one tap
- **🔁 Smart suggestions**: turn pre-filling on or off, see what Ledger learned per payee, **Forget** any of them
- 🧪 **Get test builds** switch in Settings → Phone app
- Repaid a loan / Got back can now go to **+ New person** (logs the earlier cash borrow too)

## From 8.6
- ↩️ Refunds & cashback tracker, 📅 salary month, comparisons in words, smoother Glass

## From 8.5
- 🎁 Monthly wrap, bills whose price changes later, repeating costs in budgets and My plans

## From 8.4
- Recently deleted, smarter repeat-payment suggestions, note recall, ✨ Glass theme

## Sheet script
- No new Sheet script for 8.6 (refunds are saved in your Settings tab). If you haven't yet, paste Code.gs **v10** so the Sheet keeps the new price and logs it right (it also includes v9's Recently deleted tab)
