import pandas as pd

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
    
    # Fill NaN hours with 0 for employees in roster but not in the report
    merged_df['Hours'] = merged_df['Hours'].fillna(0)
    
    # TODO: Clarify how to handle FTE == 0. For now, we replace 0 with a small number to avoid division by zero.
    # Calculate the score
    merged_df['FTE'] = merged_df['FTE'].replace(0, 1e-9)
    merged_df['Score'] = merged_df['Hours'] / merged_df['FTE']
    
    # Rank the employees
    merged_df['Rank'] = merged_df['Score'].rank(method='dense', ascending=False).astype(int)
    
    # Sort by rank
    ranked_df = merged_df.sort_values('Rank')
    
    # Rename columns to avoid spaces for template compatibility
    ranked_df = ranked_df.rename(columns={
        'First Name': 'First',
        'Last Name': 'Last'
    })
    
    return ranked_df
