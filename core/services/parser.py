import pandas as pd
from typing import IO


EXPECTED_ROSTER_COLUMNS = [
    'Qgenda Name',
    'Email Name',
    'Email Addresses',
    'FTE',
]

def parse_hours_report(file: IO) -> pd.DataFrame:
    """
    Parses the hours report Excel file.

    Args:
        file: The uploaded Excel file.

    Returns:
        A pandas DataFrame with employee names and hours for each assignment.
    """
    # Read the raw Excel file
    df_raw = pd.read_excel(file, header=None)
    
    # Extract employee names (column 0, starting from row 5)
    # Continue until we hit an empty cell or "Totals"
    employee_names = []
    row_idx = 5  # Start at row 5 (0-indexed)
    while row_idx < len(df_raw):
        name = df_raw.iloc[row_idx, 0]
        if pd.isna(name) or str(name).strip() == 'Totals':
            break
        employee_names.append(str(name).strip())
        row_idx += 1
    
    # Determine the range of rows for data extraction
    num_employees = len(employee_names)
    data_start_row = 5
    data_end_row = data_start_row + num_employees
    
    # Extract assignment names from row 3
    assignment_row = df_raw.iloc[2, :]  # Row 3 (0-indexed as 2)
    
    # Find HA columns and their assignment names
    ha_assignments = {}
    current_assignment = None
    
    for col_idx in range(len(assignment_row)):
        assignment = assignment_row.iloc[col_idx]
        if pd.notna(assignment):
            current_assignment = assignment
        
        # Check if this column has 'HA' in row 5
        measure = df_raw.iloc[4, col_idx]  # Row 5 (0-indexed as 4)
        if measure == 'HA' and current_assignment:
            ha_assignments[col_idx] = current_assignment
    
    # Create the hours DataFrame
    hours_data = {}
    for col_idx, assignment in ha_assignments.items():
        hours_data[assignment] = df_raw.iloc[data_start_row:data_end_row, col_idx].fillna(0).tolist()
    
    # Create DataFrame with employee names as index
    df = pd.DataFrame(hours_data, index=employee_names)
    
    return df

def parse_roster(file: IO) -> pd.DataFrame:
    """
    Parses the roster Excel file.

    Args:
        file: The uploaded Excel file.

    Returns:
        A pandas DataFrame with employee info (name, email, FTE).
    """
    df = pd.read_excel(file, header=0)

    actual_columns = df.columns.tolist()
    if actual_columns != EXPECTED_ROSTER_COLUMNS:
        raise ValueError(
            'Roster must contain exactly these columns in order: '
            + ' | '.join(EXPECTED_ROSTER_COLUMNS)
        )
    
    # Standardize email column name to 'Email' for consistency
    if 'Email Addresses' in df.columns:
        df = df.rename(columns={'Email Addresses': 'Email'})

    df = df.rename(columns={'Email Name': 'EmailName'})
    
    return df
