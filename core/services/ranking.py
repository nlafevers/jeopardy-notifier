import pandas as pd


def _finalize_rankings(df: pd.DataFrame) -> pd.DataFrame:
    """Apply rank labels and sort order, excluding FTE 0 employees from ranking."""
    ranked_mask = df['FTE'] > 0

    df = df.copy()
    df['DoNotRank'] = ~ranked_mask
    df['Score'] = df['Hours'] / df['FTE'].where(ranked_mask)
    df['Rank'] = ''

    if ranked_mask.any():
        ranked_scores = df.loc[ranked_mask, 'Score']
        df.loc[ranked_mask, 'Rank'] = ranked_scores.rank(method='dense', ascending=False).astype(int).astype(str)

    df.loc[~ranked_mask, 'Rank'] = 'DNR'

    ranked_df = df.loc[ranked_mask].sort_values('Score', ascending=False)
    dnr_df = df.loc[~ranked_mask].sort_values(['Hours', 'Last Name', 'First Name'], ascending=[False, True, True])

    return pd.concat([ranked_df, dnr_df], ignore_index=True)


def rank_employees(hours_df: pd.DataFrame, roster_df: pd.DataFrame, assignment: str) -> pd.DataFrame:
    """
    Ranks employees based on hours worked in a specific assignment, adjusted for FTE.

    Args:
        hours_df: DataFrame with hours worked, indexed by employee name.
        roster_df: DataFrame with employee roster information.
        assignment: The assignment to rank by.

    Returns:
        A ranked pandas DataFrame with employee, hours, FTE, and rank.
    """
    
    # Select the series for the chosen assignment
    assignment_hours = hours_df[[assignment]].rename(columns={assignment: 'Hours'})

    # Merge with roster_df. We use a right merge to keep all employees from the roster.
    merged_df = pd.merge(assignment_hours, roster_df, left_index=True, right_on='Qgenda Name', how='right')
    merged_df = merged_df.rename(columns={'Qgenda Name': 'Qgenda'})
    
    # Fill NaN hours with 0 for employees in roster but not in the report
    merged_df['Hours'] = merged_df['Hours'].fillna(0)
    
    # Rename columns to avoid spaces for template compatibility
    merged_df = merged_df.rename(columns={
        'First Name': 'First',
        'Last Name': 'Last'
    })

    return _finalize_rankings(merged_df)
