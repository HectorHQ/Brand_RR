import streamlit as st  
import requests
import json
import pandas as pd
import numpy as np
from accounting_service_payments_applications import get_bearer_token,create_headers
import os
from zipfile import ZipFile
import zipfile
import datetime as dt
import time


st.set_page_config('Brand Remittance Accounting Service',
                    page_icon= ':spiral_note_pad:',
                    layout= 'wide'
                    )

st.title(':orange[Nabis] Brand Remittance Accounting Service :spiral_note_pad:')

@st.cache_data
def load_dataframe(file):
    """
    Loads the uploaded file into a Pandas DataFrame.
    """

    file_extension = file.name.split(".")[-1]
    
    if file_extension == "csv":
        df = pd.read_csv(file)

    elif file_extension == "xlsx":
        df = pd.read_excel(file)

    return df


def remittance_report(headers,userid,organizationID,start_date,end_date):
    json_data = {
        'operationName': 'postAccountingAPIRemittanceReportGeneration',
        'variables': {
            'input': {
                'orgId': organizationID,
                'userId': userid,
                'startDate': start_date,
                'endDate': end_date,
            },
        },
        'query': 'mutation postAccountingAPIRemittanceReportGeneration($input: PostAccountingAPIRemittanceReportGenerationInput!) {\n  postAccountingAPIRemittanceReportGeneration(input: $input)\n}\n',
    }

    response = requests.post('https://api.nabis.com/graphql/admin', headers=headers, json=json_data)
    generation = response.json()
    return generation


def fetch_remittance(organizationID):
    try:
        json_data = {
            'operationName': 'getAccountingAPIFetchRemittanceReportByOrg',
            'variables': {
                'input': {
                    'orgId': organizationID,
                    'pageInfo': {
                        'numItemsPerPage': 50,
                        'page': 1,
                    },
                    'status': 'GENERATED',
                    'atLeastStartDate': None,
                    'atMostStartDate': None,
                    'atLeastEndDate': None,
                    'atMostEndDate': None,
                },
            },
            'query': 'query getAccountingAPIFetchRemittanceReportByOrg($input: GetAccountingAPIFetchRemittanceReportByOrgInput!) {\n  getAccountingAPIFetchRemittanceReportByOrg(input: $input) {\n    remittanceReports {\n      id\n      orgId\n      startDate\n      endDate\n      status\n      amount\n      s3Link\n      __typename\n    }\n    pageInfo {\n      page\n      numItemsPerPage\n      hasNextPage\n      orderBy {\n        attribute\n        order\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n',
        }

        response = requests.post('https://api.nabis.com/graphql/admin', headers=headers, json=json_data)

        report = response.json()
        id_remittance_report = report['data']['getAccountingAPIFetchRemittanceReportByOrg']['remittanceReports'][0]['id']
        status_remittance_report = report['data']['getAccountingAPIFetchRemittanceReportByOrg']['remittanceReports'][0]['status']
    except:
        st.write('Report not generated')

    return id_remittance_report,status_remittance_report    

    
def download_remitance(id_remittance_report):
    json_data = {
        'operationName': 'getAccountingAPIDownloadReportCSV',
        'variables': {
            'input': {
                'id': id_remittance_report,
            },
        },
        'query': 'query getAccountingAPIDownloadReportCSV($input: GetAccountingAPIDownloadReportCSVInput!) {\n  getAccountingAPIDownloadReportCSV(input: $input)\n}\n',
    }

    response = requests.post('https://api.nabis.com/graphql/admin', headers=headers, json=json_data)

    report_data = response.json()

    report_data = report_data['data']['getAccountingAPIDownloadReportCSV']
      

    return report_data


if __name__ == "__main__":
    
    with st.form(key='log_in',):
        
        email = st.text_input('email:'),
        password_st = st.text_input('Password:',type='password')

        submitted = st.form_submit_button('Log in')

        try:
            if submitted:
                st.write('Credentials Saved')


                user = email[0]
                password = password_st
                token,user_id = get_bearer_token(user,password)
                headers = create_headers(token)
                
        except:
            st.warning('Incorrect Email or Password, Try again')

    file_uploaded = st.file_uploader('Upload file with Brands you want to generate reports to')

    if file_uploaded:
        user = email[0]
        password = password_st
        token,userid = get_bearer_token(user,password)
        headers = create_headers(token)

        file = load_dataframe(file_uploaded)
        file = file.dropna(subset=['Brand_name'])
        list_brands = file.to_json(orient='records')
        list_brands = json.loads(list_brands)

        list_dataframes = []

        col1,col2,col3 = st.columns([0.4,0.4,0.2],gap='medium')
        with col1:
            generate_report = st.button('Generate Report')

            if generate_report:
                for idx,brand in enumerate(list_brands):
                    org_id = brand['BrandID']
                    sDate = brand['StartDate']
                    eDate = brand['EndDate']
                    brand_name = brand['Brand_name']
                    brand_name = brand_name.replace('/','_')
                    st.write(f'{brand_name}')
                    try:
                        report_generated = remittance_report(headers,userid,org_id,sDate,eDate)
                        st.write('Report Generated')
                        st.markdown('---')
                    except NameError as e:
                        st.write(f'Brand {brand_name} failed to generate remittance. {e}')

        with col2:

            download_remittance_button = st.button('Fetch and Download')

            if download_remittance_button:        
                for idx,brand in enumerate(list_brands):
                    org_id = brand['BrandID']
                    sDate = brand['StartDate']
                    eDate = brand['EndDate']
                    brand_name = brand['Brand_name']
                    brand_name = brand_name.replace('/','_')
                    st.write(f'{brand_name}')
                    try:
                        id_remittance_report,status = fetch_remittance(org_id)
                        st.write(f'{status} / {id_remittance_report}')
                        st.markdown('---')
                        download_report = download_remitance(id_remittance_report)
                        if download_report is not None:
                            if len(download_report)>0:

                                df = pd.read_csv(download_report)
                                temp_tup = []
                                temp_tup.append(df)
                                temp_tup.append(brand_name)
                                temp_tup.append(sDate)
                                temp_tup.append(eDate)
                                list_dataframes.append(temp_tup)
                            else:
                                continue    
                        else:
                            continue            

                    except NameError as e:
                        st.text(f'Brand {brand_name} failed to generate remittance. {e}')
                        st.markdown('---')
                        continue

            
        with col3:    
            if len(list_dataframes) > 0:
                # Create a zip file
                with zipfile.ZipFile('dataframes.zip', 'w') as zipf:
                    # Iterate over each dataframe
                    for item in list_dataframes:
                        brand_name = item[1]
                        startPeriod = item[2]
                        startPeriod_s = startPeriod / 1000
                        startPeriod_date = dt.datetime.utcfromtimestamp(startPeriod_s).strftime('%m-%d-%Y')
                        endPeriod = item[3]
                        endPeriod_s = endPeriod / 1000
                        endPeriod_date = dt.datetime.utcfromtimestamp(endPeriod_s).strftime('%m-%d-%Y')
                        df = item[0]
                        file_name = f'{brand_name} period {startPeriod_date} to {endPeriod_date}.csv'
                        # Convert dataframe to csv and save it in the zip file
                        df.to_csv(file_name, index=False)
                        zipf.write(file_name)
                        
                with open('dataframes.zip','rb')as fp:
                    st.download_button('Download Reports',data=fp,file_name='Remittances_Reports.zip',mime='application/zip')

                    
                 

            
            