# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

DEFAULT_SCALE = 10_000

def optimize_keyword_ranks(df: pd.DataFrame, budget: int, scale: int = DEFAULT_SCALE):
    df = df.copy()

    forced_rows = []
    forced_kw = set()

    for kw, sub in df.groupby('키워드'):
        r1 = sub[sub['순위'] == 1]
        if not r1.empty:
            row = r1.iloc[0]
            if row['비용'] == 0 and row['클릭'] == 0:
                forced_rows.append(row.name)
                forced_kw.add(kw)

    forced_cost = df.loc[forced_rows, '비용'].sum() if forced_rows else 0
    forced_clicks = df.loc[forced_rows, '클릭'].sum() if forced_rows else 0

    remaining_budget = budget - forced_cost
    if remaining_budget < 0:
        raise ValueError("예산 부족: 강제 키워드 비용보다 적습니다.")

    df['비용단위'] = np.ceil(df['비용'] / scale).astype(int)
    budget_unit = remaining_budget // scale

    dp_df = df[~df.index.isin(forced_rows)]
    dp_keywords = [kw for kw in df['키워드'].unique() if kw not in forced_kw]

    options_per_keyword = []
    for kw in dp_keywords:
        sub = dp_df[dp_df['키워드'] == kw]
        opts = [(int(row['비용단위']), int(row['클릭']), idx)
                for idx, row in sub.iterrows()
                if row['비용단위'] <= budget_unit]

        if not opts:
            raise ValueError(f"'{kw}' 예산 내 선택 옵션 없음")

        options_per_keyword.append(opts)

    n = len(dp_keywords)
    if n == 0:
        return df.loc[forced_rows].copy(), forced_cost, forced_clicks

    DP = [[-1] * (budget_unit + 1) for _ in range(n + 1)]
    choice = [[None] * (budget_unit + 1) for _ in range(n + 1)]
    DP[0][0] = 0

    for i in range(1, n + 1):
        opts = options_per_keyword[i - 1]
        for b in range(budget_unit + 1):
            best_click = -1
            best_choice = None
            for cost_u, clicks, idx in opts:
                if cost_u <= b and DP[i-1][b-cost_u] != -1:
                    cand = DP[i-1][b-cost_u] + clicks
                    if cand > best_click:
                        best_click = cand
                        best_choice = (cost_u, clicks, idx)
                    elif cand == best_click and best_choice is not None:
                        if cost_u < best_choice[0]:
                            best_choice = (cost_u, clicks, idx)
            DP[i][b] = best_click
            choice[i][b] = best_choice

    best_b = max(range(budget_unit+1), key=lambda b: DP[n][b])
    if DP[n][best_b] < 0:
        raise ValueError("예산 내 최적해 없음")

    selected = []
    b = best_b
    for i in range(n, 0, -1):
        c = choice[i][b]
        cost_u, clicks, idx = c
        selected.append(idx)
        b -= cost_u
    selected.reverse()

    final = forced_rows + selected
    result_df = df.loc[final].copy()
    total_cost = result_df["비용"].sum()
    total_clicks = result_df["클릭"].sum()

    return result_df, total_cost, total_clicks
