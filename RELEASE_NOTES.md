## Brokeless v9.3 · What's new

- **📆 Turn a card purchase into EMI**: open the purchase (e.g. Mobile ₹17,268 on ICICI Credit Card) → **📆 Turn into EMI** → pick months (3/6/9/12/18/24 or any) and type the EMI from your bank. It shows the total you pay and the **extra (interest + fees)**. The purchase stays in your spending on the day you bought it; the card gets it back (the bank moves it off this bill) and **each month's EMI is logged by itself on the card's bill day**, so the card's "what you owe" matches the bank. The card's limit use still counts the EMI amount left
- **📩 The bank's "converted into EMI" SMS**: becomes one line in the 🔔 bell, **"₹17,268 turned into EMI · Link"**. Link opens the EMI screen with the purchase, months and EMI already filled in. "Convert to EMI" offers are ignored
- **📆 EMI from a bank SMS**: an SMS with the same amount as one of your EMIs (or saying "EMI") is filled in as **📆 EMI · Bike loan** for this month, not as an expense. If that EMI was already logged, the SMS is filed with it so nothing is counted twice. EMIs can be set to **⚡ log themselves** each month (Edit EMI)
- **No double counting**: a purchase on EMI counts once as spending; afterwards only the EMI's extra (interest, fees) counts in reports, savings rate and money flow
- **#tags in small letters**: #Car, #CAR and #car are one tag. New notes save tags in small letters, and older notes are tidied once
- **Note ideas without repeats**: "Uber" and "uber" show as one idea
- **💗 Pulse → Career: new Analysis**: a CTC card, tiles for in hand a month, what reaches your bank, growth a year and time at this job, a **Where your CTC goes** bar (in hand, bonus, tax, PF, other), **Spending vs take-home**, and tips (next review target, where tax starts for you)
- **🧮 Hike calculator** (end of Career): start from your CTC or any amount (yearly or monthly), pick a hike % or type a new offer. **⚙️ Your salary structure**: yearly performance bonus (kept out of the monthly in-hand, shown after tax), PF (up to ₹3,000 under the new ₹25,000 PF ceiling, 12% of basic, your own amount, or none), basic %, other monthly cuts, professional tax, and **Match my real salary**. Saved and used everywhere
- **Smart tax alerts**: shows the CTC where income tax starts for you and the **tax trap** just after it (a CTC that takes home *less* than at the line), with **"ask for at least ₹X"**. Every hike shows its **real raise** (what you take home), tax a year, take-home a year, and a 10/15/20/30% compare
- **Indian commas in every amount box**: 100000 shows as 1,00,000 while you type, and when you edit an entry (EMI, goal, card limit, loan, budget… not only the big ₹ box)
- **Smaller home-screen widgets**: each widget is now one row high by default (Free to spend 4×1, Spent 3×1, Needs you 3×1, Pulse 2×1). Already placed widgets keep their size: long-press → resize, or remove and add again
- **SMS blocked on a phone?** Clearer steps: try Allow once in phone settings first, which makes "Allow restricted settings" appear in the ⋮ menu

## Brokeless v9.2 · What's new

- **🔔 Update notifications outside the app**: when a new version is out, the phone now shows a pop-up notification (it used to sit silently in the notification shade). Brokeless checks every 4 hours instead of 12, also checks when an SMS arrives, and reminds you once 2 days later if you haven't installed it
- **⇄ Moved money between your own banks? One tap**: the bank SMS (money out of ICICI) and the other bank's SMS (money into Kotak) are joined into one line in the bell: **"Moved ₹5,000 to Kotak Bank?" → ✓ Yes, moved**. Logged as a transfer, never as an expense or income. Already logged it, or filed one side as a transfer? The other SMS is filed quietly, so nothing is counted twice
- **An SMS that names your other account** ("credited to A/c XX1211", "self transfer") is filled in as a transfer to that account
- **Fixed: the second SMS of a UPI self-transfer was dropped** (both SMS carry the same UPI reference)
- **Fixed: "Acc XX616"** in an ICICI SMS is now read as the account number even when the SMS mentions a second account
- **✨ Suggestions for a first-time payee**: the Money paid screen now suggests your matching **bill** (same amount, due around now), what you logged for **the same amount before**, a transfer to **your own account**, and the category from the name. A matching bill is filled in and marked paid
- **Money paid screen has what the + screen has**: **👥 Split bill** (your share is the expense, friends owe you the rest), **For me · I'll pay back** when paid from Mom's or Evol's money, **#tags**, and **📷 bill photo** (with your own Sheet script)
- **Note ideas**: your usual notes for the picked category, plus your #tags, under the Note box
- **🎯 Goals: monthly instalment**: set "Monthly instalment ₹" on a goal. The goal shows a **% bar**, the target, **"3 of 11 instalments · 8 months left · done by Jun 2027"**, and whether this month's instalment is in. **+ Add money** fills in what is left for this month

## Brokeless v9.1 · What's new

- **Ready for Android 16**: the app now targets Android 16, which Google Play requires. On Android 15 and 16 phones the screen is laid out to stay clear of the status bar, the gesture bar and the keyboard
- **Google Play build**: a separate build for the Play Store (app ID `com.brokeless.app`) with no self-updater, since Play does the updating. The link-installed app keeps updating itself as before
- **📊 Monthly report in the app** (Settings → Monthly report): spent vs last month, income, what was left over, average per day, where it went with budgets, the 5 biggest spends and card dues. Use ‹ › for any month
- **✉️ Send to my email**: opens your mail app with the report already written and addressed to your Google account. You tap Send. Works with Google sign-in, no extra permission
- **🔔 On the 1st**: a phone notification and a line in the bell say last month's report is ready. Switch it off on the same page

## Brokeless v9.0 · What's new

- **SMS access blocked by the phone?** The set-up screen now has an **Open Brokeless in phone settings** button with the two taps to do there (⋮ → Allow restricted settings)
- **Settings → Permissions & phone app** (was "Phone app"): shows SMS, Notifications and Battery at a glance, with a button to open the phone's own settings for Brokeless
- **📲 Permissions asked at set-up**: after your balances, one screen with **Read bank SMS**, **Notifications** and **Battery: Unrestricted**, each with what it is for and one button. If Android blocks SMS access for an app installed from a link, it shows the exact steps
- **With Google sign-in, no more "Connect the Sheet first"**: Email reports and the Google Calendar tick are hidden (they only work with your own Sheet script). Settings → Google Drive & sync explains where your data is saved, with **Open my Sheet**
- **Fixed: Sign in with Google stopped at "Unsupported locale: en_IN"** while making your Sheet
- **🔑 → Google: switch your own Brokeless to Google sign-in** (Settings → Google Sheet & sync → Switch to Google sign-in). No more URL and secret key. Everything on your phone is copied into a private "Brokeless" Sheet in your Drive and counted; your old Sheet stays untouched as a spare. If anything fails half-way you stay exactly where you were
- **☁️ Daily Drive backup with Google sign-in**: a copy is saved in Drive → "Brokeless backups" the first time you open the app each day. Settings → Backups: back up now, restore (a safety copy is made first), delete, keep last 7 / 15 / 30
- **🏦 Pick your banks** on first set-up: tap your banks, cards and wallets (initials in each bank's colour), then type the balances. Bank SMS are matched to them automatically, and more banks are recognised (Canara, Union, BOI, IDBI, Indian, IOB, UCO, Bandhan, HSBC and more)
- **👋 Quick tour**: 5 swipe cards after set-up, with **Skip** on every card
- **📖 How it works** (Settings): a short guide for each part of the app, each with a button that takes you there, plus "Play the tour"
- **Fixed: page moving behind a pop-up**: swiping up or down on a card / account screen no longer scrolls the page behind it
- **Fixed: tabs jumping back**: on Money (Accounts · Income · Transfers · Invest · EMIs · Loans) tapping EMIs or Loans keeps the row where you swiped it, with the tab you picked in view
- **Card showing its limit as a balance** (e.g. ₹1,49,271): now flagged ⚠️ on the card with a **Fix** button that fills in the limit and what you owe. **Match** on a card now asks "what you owe", never the limit left
- **💳 Pay your card any day**: tap the card (Money → Accounts) → **Pay**. Full amount or a part, before or after the bill day
- **💳 Card bill from SMS, one tap**: when you pay the card, the bank SMS (money out) and the card SMS (payment received) are joined into one line in the bell: **"Paid ICICI Credit Card ₹30?" → ✓ Yes, I paid**. Already logged it with Pay? Both SMS are filed quietly. The phone notification says "card payment received · tap to confirm"
- **📊 How much of the limit is used**: each card shows % used and how much is left before **your safe line (30%, change it in the card's Edit screen)**. A heads-up appears in the bell when you cross it
- **Paying the card is never a second expense**: a card spend counts on the day you swipe; paying the bill only moves money bank → card
- Fixed: bank SMS showing "Dispute Call 1800…" as the payee

- **Ledger is now Brokeless** 💸 Same app, same data, new name
- **🔐 Sign in with Google**: new users get a private Brokeless Sheet in their own Google Drive. Use it on any phone or laptop; nobody else can see it
- **New-user setup** with clean defaults: bank, cash and card, default categories, generic bill presets
- **💬 Feedback** now reaches the app maker's inbox

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
