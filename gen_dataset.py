import random
import csv
from datetime import date, timedelta

random.seed(42)  # fixed seed so the dataset is reproducible
ACCOUNTS = {'ACC2001': 'CUS601', 'ACC2002': 'CUS602', 'ACC2003': 'CUS603', 'ACC2004': 'CUS604', 'ACC2005': 'CUS605',
            'ACC2006': 'CUS606'}  # accounts 2001-2005 are MUR, account 2006 is USD
CCY = {a: ('USD' if a == 'ACC2006' else 'MUR') for a in ACCOUNTS}
START = date(2026, 7, 1)
DAYS = 92  # July, August and September 2026
OUT = [('Groceries', 40, 350, 'POS'), ('Restaurant', 60, 280, 'MOBILE'), ('Fuel', 80, 260, 'POS'),
       ('Transport', 20, 120, 'MOBILE'), ('Utilities', 300, 1200, 'ONLINE'), ('Insurance', 800, 1500, 'TRANSFER'),
       ('Pharmacy', 150, 600, 'POS'), ('Electronics', 900, 3000, 'ONLINE'), ('Streaming', 60, 150, 'ONLINE'),
       ('Clothing', 300, 1400, 'POS'), ('Entertainment', 100, 400, 'ONLINE'), ('Health', 200, 900, 'POS')]
IN = [('Transfer In', 500, 4000, 'MOBILE'), ('Refund', 80, 600, 'ONLINE'), ('Cashback', 20, 250, 'ONLINE'),
      ('Deposit', 2000, 9000, 'BRANCH')]
BRANCH = {'POS': 'BR01', 'MOBILE': 'BR02', 'ONLINE': 'BR03', 'TRANSFER': 'BR02', 'BRANCH': 'BR04'}

rows = []
opening = {}
for acc, cus in ACCOUNTS.items():
    ccy = CCY[acc]
    scale = 1.0 if ccy == 'MUR' else 0.024  # USD amounts are about 1/42 of MUR amounts
    bal = round(random.uniform(8000, 20000) * scale, 2)
    opening[acc] = bal
    for d in range(DAYS):
        day = START + timedelta(days=d)
        if day.day == 25:  # monthly salary
            amt = round(random.uniform(18000, 32000) * scale, 2)
            bal = round(bal + amt, 2)
            rows.append([acc, cus, day.isoformat(), f'{random.randint(7, 9):02d}:{random.randint(0, 59):02d}:00',
                         'CREDIT', f'{amt:.2f}', ccy, 'Salary', 'TRANSFER', 'BR02', f'{bal:.2f}', 'SUCCESS'])
        for _ in range(random.choice([0, 0, 1])):  # about one transaction every third day
            if random.random() < 0.2:  # some money comes in
                cat, lo, hi, ch = random.choice(IN)
                kind = 'CREDIT'
                amt = round(random.uniform(lo, hi) * scale, 2)
                bal = round(bal + amt, 2)
            else:
                cat, lo, hi, ch = random.choice(OUT)
                kind = 'DEBIT'
                amt = round(random.uniform(lo, hi) * scale, 2)
                bal = round(bal - amt, 2)
            status = 'FAILED' if random.random() < 0.03 else 'SUCCESS'
            rows.append([acc, cus, day.isoformat(), f'{random.randint(7, 21):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}',
                         kind, f'{amt:.2f}', ccy, cat, ch, BRANCH[ch], f'{bal:.2f}', status])

# a few large transfers out, two of them above the 10,000 MUR review threshold

rows.append(['ACC2002', 'CUS602', '2026-08-14', '11:02:17', 'DEBIT', '12500.00', 'MUR', 'Transfer Out', 'TRANSFER', 'BR02', '0.00', 'SUCCESS'])
rows.append(['ACC2004', 'CUS604', '2026-09-03', '15:40:05', 'DEBIT', '10800.00', 'MUR', 'Transfer Out', 'TRANSFER', 'BR02', '0.00', 'SUCCESS'])
rows.sort(key=lambda r: (r[2], r[3]))  # order by date then time, like a real feed

# recompute balance_after in the sorted order, so every running balance is consistent
running = dict(opening)
for r in rows:
    acc, amt = r[0], float(r[5])
    if r[11] == 'SUCCESS' and r[4] in ('CREDIT', 'DEBIT'):
        running[acc] = round(running[acc] + amt if r[4] == 'CREDIT' else running[acc] - amt, 2)
    r[10] = f'{running[acc]:.2f}'  # the balance_after column

def pick(pred, k=0):
    hits = [i for i, r in enumerate(rows) if pred(r)]
    return hits[k] if len(hits) > k else hits[-1]

# deliberate data quality issues
dup_idx = pick(lambda r: r[0] == 'ACC2002' and r[4] == 'DEBIT', 2)
rows.insert(dup_idx + 1, list(rows[dup_idx]))                      # 1. exact copy under a new ID
rows[pick(lambda r: r[0] == 'ACC2003', 5)][5] = ''                   # 2. missing amount
rows[pick(lambda r: r[0] == 'ACC2004', 4)][0] = ''                   # 3. missing account_id
rows[pick(lambda r: r[0] == 'ACC2001', 7)][2] = '2026-09-31'         # 4. impossible date
rows[pick(lambda r: r[0] == 'ACC2005', 6)][5] = '-150.00'            # 5. negative amount
rows[pick(lambda r: r[0] == 'ACC2002' and r[4] == 'DEBIT', 0)][4] = 'debit '  # 6. messy text
rows[pick(lambda r: r[0] == 'ACC2001' and r[4] == 'DEBIT', 0)][6] = 'mur'     # 7. lowercase currency
rows[pick(lambda r: r[0] == 'ACC2003', 9)][7] = ''                   # 8. blank category
rows[pick(lambda r: r[0] == 'ACC2001' and r[4] == 'DEBIT', 4)][11] = 'FAILED'  # 9. failed debit

header = ['transaction_id', 'account_id', 'customer_id', 'transaction_date', 'transaction_time', 'transaction_type',
          'amount', 'currency', 'merchant_category', 'channel', 'branch_code', 'balance_after', 'status']
with open('bank_transactions_agentic.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(header)
    for n, r in enumerate(rows, start=1):
        w.writerow([f'TXN{n:04d}'] + r)
print('rows:', len(rows), '| accounts:', len(ACCOUNTS))
