# -*- coding: utf-8 -*-
"""
Created on Sat Nov  9 11:51:35 2024

@author: User
"""

import streamlit as st
import pandas as pd
from datetime import timedelta
from io import BytesIO

# Set the title for the main page
st.title("Fuel Transaction Validation App")

# Step 1: Upload files in the sidebar
st.sidebar.header("Upload Files")
uploaded_file1 = st.sidebar.file_uploader("Upload Soliduz NTS Transaction File (Excel)", type=["xlsx"])
uploaded_file2 = st.sidebar.file_uploader("Upload NTS Fuel Alert Report File (Excel)", type=["xlsx"])

# Sidebar slider for setting the time buffer
time_buffer = st.sidebar.slider("Set Time Matching Buffer (in hours)", min_value=0, max_value=24, value=1)

if uploaded_file1 and uploaded_file2:
    # Step 2 & 3: Read and preprocess the 1st file
    df1 = pd.read_excel(uploaded_file1)
    df1['TransactionDateTime'] = pd.to_datetime(df1['TransactionDate'].astype(str) + ' ' + df1['TransactionTime'].astype(str))
    df1 = df1.drop(columns=['TransactionDate', 'TransactionTime'])

    # Step 5 & 6: Read and preprocess the 2nd file
    df2 = pd.read_excel(uploaded_file2, skiprows=4)
    df2['Alert Time'] = pd.to_datetime(df2['Alert Time'])

    # Step 1: Store the value for 'DstbSum (km)' in df2
    df2['DstbSum (km)'] = df2['DstbSum (km)']

    # Step 2: For 'Alert' = 'Refuel', divide 'DstbSum (km)' by 1000
    df2.loc[df2['Alert'] == 'Refuel', 'DstbSum (km)'] /= 1000

    # Step 3: Store the value for 'Odometer' in df1
    if 'Odometer' not in df1.columns:
        st.error("The column 'Odometer' is missing in file1.")
        st.stop()

    # Display data for confirmation
    st.write("Soliduz NTS Transaction Data (1st File)", df1)
    st.write("NTS Fuel Alert Report Data (2nd File)", df2)

    # Step 7: Matching logic based on Vehicle Registration and buffered Time
    matched_data = []
    unmatched_data = []

    for idx, row1 in df1.iterrows():
        # Check if there is a match in df2 for the current row in df1 within the buffer range
        matches = df2[
            (df2['Vehicle Number'] == row1['VehicleRegistrationNo']) &
            (df2['Alert Time'] >= row1['TransactionDateTime'] - timedelta(hours=time_buffer)) &
            (df2['Alert Time'] <= row1['TransactionDateTime'] + timedelta(hours=time_buffer)) &
            (df2['Alert'] == 'Refuel')
        ]
        
        if not matches.empty:
            # If match found, add matched columns from df2
            matched_row = pd.concat([row1, matches.iloc[0][['Vehicle Number','Alert Time', 'Alert', 'Difference (L)','Fuel Remain (L)', 'Fuel Remain (%)', 'RPM', 'DstbSum (km)', 'Location']]])
            matched_row['MatchStatus'] = 'Matched'
            matched_data.append(matched_row)
        else:
            # If no match found, keep the row and mark it as unmatched
            unmatched_row = pd.concat([row1, pd.Series([None] * 9, index=['Vehicle Number','Alert Time', 'Alert', 'Difference (L)','Fuel Remain (L)', 'Fuel Remain (%)', 'RPM', 'DstbSum (km)', 'Location'])])
            unmatched_row['MatchStatus'] = 'Unmatched'
            unmatched_data.append(unmatched_row)

    # Combine matched and unmatched data into a single DataFrame
    validated_df = pd.DataFrame(matched_data + unmatched_data)

    # Step 9: Display the results
    st.write("Validated Transactions", validated_df)

    # Step 10: Option to download the validated file
    def convert_df(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Validated_Transactions')
        processed_data = output.getvalue()
        return processed_data

    excel_data = convert_df(validated_df)
    st.download_button("Download Validated Data", data=excel_data, file_name="Validated_Transactions.xlsx", mime="application/vnd.ms-excel")
