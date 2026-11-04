## Ledger v8.6 · What's new

## New
- **↩️ Refunds & cashback tracker**: when IRCTC, Swiggy, Zomato, Amazon, Flipkart or your bank texts "refund initiated" or "cashback will be credited", Ledger saves it in a **Refunds** list: from where, why (e.g. "Ticket cancelled · PNR 4521897632"), how much, which bank or card it goes back to, and the expected-by date. Open it from Money → Income, Insights, the 🔔 bell, or ask ✨ "any refunds pending?"
- **Late refunds get flagged**: if the money hasn't come by the expected date, the bell tells you how many days late it is and what to quote when you contact the seller
- **Refunds are matched automatically**: when the bank SMS for the money arrives, Ledger recognises it, picks the right refund and fills the form for you
- **A refund cancels the spend it came from**: a ₹400 Swiggy refund lowers your Food spending by ₹400 (it shows as **+₹400 ↩️** in your list). **Cashback** is logged as income
- **Expecting a refund?** Open any expense → "↩️ I'm expecting a refund for this", or add one by hand in Refunds

## Better
- **📅 Salary month** (Money → Income): a salary credited on or after the 25th now counts for the next month. No more double-salary October when you changed jobs, and no empty-looking November. Bank balances still use the real date. Change the day or turn it off any time
- **Where it went**: tap a slice and its name, amount and % show inside the ring (no more box covering "Spent")
- **Goals**: cleaner buttons, just **+ Add money** and **Withdraw** (withdraw, then transfer or spend as usual)
- **Home cards** are even and fit the screen; your **Kotak** card shows the total including Mom & Evol
- **New entry**: category tiles are centred and long names like Transportation fit their tile
- A little more space under the top bar on every tab
- A newly installed app now always shows its own new screens
- **Insights comparisons in plain words**: "↑ 36% more than Oct" / "↓ 20% less than Oct" instead of ▲▼ triangles. Green = good for you, red = not
- **Saved %** no longer shows crazy numbers like −6261% before your salary arrives: it says "salary not in yet"
- **Spent** shows how much came back as refunds; Entries, Biggest and No-spend days ignore refunds
- **Glass is much smoother**: new "Glass effect" setting (Settings → Appearance). **⚡ Smooth** (default) keeps the see-through look without blurring every card; **💎 Full blur** is the old look for fast phones
- Tile labels, numbers and the bottom bar no longer get cut off with large phone text

## From 8.5
- 🎁 Monthly wrap, bills whose price changes later, repeating costs in budgets and My plans

## From 8.4
- Recently deleted, smarter repeat-payment suggestions, note recall, ✨ Glass theme

## Sheet script
- No new Sheet script for 8.6 (refunds are saved in your Settings tab). If you haven't yet, paste Code.gs **v10** so the Sheet keeps the new price and logs it right (it also includes v9's Recently deleted tab)
