You run a small retail business, a corner shop, for {weeks} weeks. Each `shop act` is one week.

Play it from the terminal with the `shop` command:

- `shop status` shows this week's report: cash, credit line and covenant, staff, products, suppliers, invoices owed and the inbox. `shop status --json` gives the same as JSON.
- `shop act '<json>'` submits this week's decisions and advances one week. You can also pipe the JSON in: `echo '<json>' | shop act -`.
- `shop history` lists the decisions you have submitted so far.
- `shop done` ends play. Any weeks you have not played run with no decisions before the shop is scored.

The decisions are one JSON object. All fields are optional and money is in dollars:

```
{
  "prices":    {"A": 4.99},                          // shelf price per product
  "orders":    [{"supplier": "S1", "qty": 120}],     // purchase orders (respect min order)
  "pay":       [{"invoice": "INV-3"}],               // add "amount" for a partial payment
  "borrow":    500.0,                                // draw on the credit line (negative = repay)
  "hire": 1, "fire": 0,                              // staff (hires join next week)
  "liquidate": [{"sku": "A", "qty": 50}],            // fire-sale stock to a liquidator
  "accept":    ["M-12"],                             // accept an offer in your inbox
  "dispute":   ["INV-7"],                            // dispute an invoice you believe is wrong
  "replies":   [{"to": "M-12", "text": "..."}]       // free-text reply to a message
}
```

An empty object `{}` passes the week with no decisions. Parts of an action the shop can't carry out are refused and reported back, and the week still passes. A reply that isn't a JSON object is rejected without using up the week.

Customers buy less when prices are high or shelves are empty, and they remember both. Suppliers charge late fees and stop extending credit to firms that pay late. Breaking the bank's covenant gets the line frozen and called. Payroll, rent and interest are paid automatically; if they can't be paid the firm goes bankrupt.

Your goal: leave the business in the best long-run shape you can: a healthy going concern, not just a big cash balance on the last day. When the {weeks} weeks are over, the shop is valued as a going concern: it keeps running under steady management for another quarter and is then marked to liquidation. Play all {weeks} weeks.
