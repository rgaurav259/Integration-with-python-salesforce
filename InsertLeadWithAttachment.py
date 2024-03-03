import json
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
import base64
import requests

# make sure to import all the packages first

params = {
    "grant_type": "password",
    "client_id": "3MVG929eOx29turGQ9qfKpzHNh5Z878vSkObxMKP56pNJ4GbYCNyjeCMbgeYs8XvPkxj0LswyAqnI9mWxGNI4",
    "client_secret": "EF751433AF2DF98CCF65C86D25792E3314C343AFCC2FE5F47465B9D6EC210145",
    "username": "gaurav_experience-cloud@kreyaconsulting.com",
    "password": "g1a2u3r4ShKGCqycJfvdLGk0AIf5Smz3c"  # without any space
}
r = requests.post("https://login.salesforce.com/services/oauth2/token", params=params)
access_token = r.json().get("access_token")
instance_url = r.json().get("instance_url")
print("Access Token:", access_token)
print("Instance URL", instance_url)


def sf_api_call(action, parameters={}, method='get', data={}):
    headers = {
        'Content-type': 'application/json',
        'Accept-Encoding': 'gzip',
        'Authorization': 'Bearer %s' % access_token
    }
    if method == 'get':
        r = requests.request(method, instance_url + action, headers=headers, params=parameters, timeout=30)
    elif method in ['post', 'patch']:
        r = requests.request(method, instance_url + action, headers=headers, json=data, params=parameters, timeout=10)
    else:
        raise ValueError('Method should be get or post or patch.')
    print('Debug: API %s call: %s' % (method, r.url))
    if r.status_code < 300:
        if method == 'patch':
            return None
        else:
            return r.json()
    else:
        raise Exception('API error when calling %s : %s' % (r.url, r.content))


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('insertLeadWithAttachment.html')


@app.route('/submit', methods=['POST'])
def submit():
    # Get form data from the request
    first_name = request.form['firstName']
    last_name = request.form['lastName']
    company = request.form['company']
    Email = request.form['Email']
    coupon_discount = request.form['couponDiscount']

    # Query Coupon_Discount__c to check if the coupon is valid
    coupon_query = sf_api_call('/services/data/v60.0/query/', parameters={
        'q': f"SELECT Id, Coupon_Number__c FROM Coupon_Discount__c WHERE Coupon_Number__c = '{coupon_discount}'"
    })

    if coupon_query['records']:
        # Valid coupon found, proceed to create Lead
        # Salesforce REST API endpoint for creating a Lead
        api_endpoint = f"{instance_url}/services/data/v60.0/sobjects/Lead/"

        # Prepare data for the Lead object
        lead_data = {
            'FirstName': first_name,
            'LastName': last_name,
            'Company': company,
            'Email':Email
        }

        # Prepare headers with authorization token
        headers = {
            'Authorization': 'Bearer ' + access_token,
            'Content-Type': 'application/json'
        }

        # Create the Lead
        response = requests.post(api_endpoint, headers=headers, json=lead_data)

        if response.status_code == 201:
            # Lead created successfully, proceed to upload file
            lead_id = response.json().get('id')
            upload_file(lead_id)
            return 'Lead created successfully with attachments'
        else:
            # Error creating Lead
            return jsonify({'error': 'Failed to create Lead'})
    else:
        # Invalid or expired coupon
        return jsonify({'error': 'Invalid or expired coupon'})



@app.route('/upload', methods=['POST'])
def upload_file(lead_id):
    file = request.files['file']
    if file:
        encoded_string = base64.b64encode(file.read()).decode("utf-8")
        content_version = sf_api_call('/services/data/v60.0/sobjects/ContentVersion', method="post", data={
            'Title': file.filename,
            'PathOnClient': file.filename,
            'VersionData': encoded_string,
        })
        content_version_id = content_version.get('id')
        content_version = sf_api_call(f'/services/data/v60.0/sobjects/ContentVersion/{content_version_id}')
        content_document_id = content_version.get('ContentDocumentId')

        # Create a ContentDocumentLink
        content_document_link = sf_api_call('/services/data/v60.0/sobjects/ContentDocumentLink', method='post', data={
            'ContentDocumentId': content_document_id,
            'LinkedEntityId': lead_id,
            'ShareType': 'V'
        })

        return f'Successfully uploaded {file.filename} and linked to record with Id {lead_id}!'
    else:
        return 'No file uploaded.'


if __name__ == '__main__':
    app.run(debug=True)