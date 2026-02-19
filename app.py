import requests
from flask import Flask, request, jsonify

from config import (
    KEYCLOAK_SERVER_URL,
    REALM_NAME_INTERNAL,
    REALM_NAME_EXTERNAL,
    CLIENT_ID_INTERNAL,
    CLIENT_ID_EXTERNAL,
    CLIENT_SECRET_INTERNAL,
    CLIENT_SECRET_EXTERNAL, NH_MONOLITHIC_APPLICATION_SERVICE,
)

app = Flask(__name__)


# Helper to get admin access token
def get_admin_token(client_id: str,
                    client_secret: str,
                    realm: str):
    url = f"{KEYCLOAK_SERVER_URL}/realms/{realm}/protocol/openid-connect/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Failed to get admin token: {response.text}")


def get_role_by_name(role_name: str,
                     token: str,
                     realm: str):
    role_url = f"{KEYCLOAK_SERVER_URL}/admin/realms/{realm}/roles"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(role_url, headers=headers)

    if response.status_code == 200:
        roles = response.json()
        for role in roles:
            if role["name"] == role_name:
                return role
        raise Exception(f"Role '{role_name}' not found in realm.")
    else:
        raise Exception(f"Failed to fetch roles: {response.text}")


# Endpoint to create a user
@app.route("/nh-monolithic-application/v1/patient", methods=["POST"])
def create_user_internal():
    create_internal()
    return requests.post(f"{NH_MONOLITHIC_APPLICATION_SERVICE}/nh-monolithic-application/v1/patient",
                         data=request.json).json()


# Endpoint to create a user
@app.route("/nh-monolithic-application/v1/medical/member", methods=["POST"])
def create_user_external():
    create_external()
    return requests.post(f"{NH_MONOLITHIC_APPLICATION_SERVICE}/nh-monolithic-application/v1/medical/member",
                         data=request.json).json()


def create_internal():
    try:
        # Parse request body
        data = request.json
        name = data["name"]
        surname = data["surname"]
        fiscal_code = data["fiscalCode"]  # Used as username
        role_list = data["roles"]

        # Get admin token
        token = get_admin_token(client_id=CLIENT_ID_INTERNAL,
                                client_secret=CLIENT_SECRET_INTERNAL,
                                realm=REALM_NAME_INTERNAL)

        # Create user in Keycloak
        user_url = f"{KEYCLOAK_SERVER_URL}/admin/realms/{REALM_NAME_INTERNAL}/users"
        user_payload = {
            "username": fiscal_code,
            "firstName": name,
            "lastName": surname,
            "enabled": True,
            "credentials": [
                {"type": "password", "value": "TemporaryPass123!", "temporary": False}
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        user_response = requests.post(user_url, json=user_payload, headers=headers)

        if user_response.status_code not in (200, 201):
            return jsonify({"error": "Failed to create user", "details": user_response.text}), 400

        # Get created user ID
        user_id = user_response.headers.get("Location").split("/")[-1]

        # Assign roles to the user
        for role in role_list:
            role_data = get_role_by_name(role, token, REALM_NAME_INTERNAL)
            role_url = f"{KEYCLOAK_SERVER_URL}/admin/realms/{REALM_NAME_INTERNAL}/users/{user_id}/role-mappings/realm"
            role_payload = [role_data]
            role_response = requests.post(role_url, json=role_payload, headers=headers)

            if role_response.status_code not in (200, 204):
                return jsonify({"error": "Failed to assign role", "details": role_response.text}), 400

        return jsonify({"message": "User created successfully", "user_id": user_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def create_external():
    try:
        # Parse request body
        data = request.json
        name = data["patientName"]
        surname = data["patientSurname"]
        fiscal_code = data["patientFiscalCode"]  # Used as username
        role_list = ["patient"]

        # Get admin token
        token = get_admin_token(client_id=CLIENT_ID_EXTERNAL,
                                client_secret=CLIENT_SECRET_EXTERNAL,
                                realm=REALM_NAME_EXTERNAL)

        # Create user in Keycloak
        user_url = f"{KEYCLOAK_SERVER_URL}/admin/realms/{REALM_NAME_EXTERNAL}/users"
        user_payload = {
            "username": fiscal_code,
            "firstName": name,
            "lastName": surname,
            "enabled": True,
            "credentials": [
                {"type": "password", "value": "TemporaryPass123!", "temporary": False}
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        user_response = requests.post(user_url, json=user_payload, headers=headers)

        if user_response.status_code not in (200, 201):
            return jsonify({"error": "Failed to create user", "details": user_response.text}), 400

        # Get created user ID
        user_id = user_response.headers.get("Location").split("/")[-1]

        # Assign roles to the user
        for role in role_list:
            role_data = get_role_by_name(role, token, REALM_NAME_EXTERNAL)
            role_url = f"{KEYCLOAK_SERVER_URL}/admin/realms/{REALM_NAME_EXTERNAL}/users/{user_id}/role-mappings/realm"
            role_payload = [role_data]
            role_response = requests.post(role_url, json=role_payload, headers=headers)

            if role_response.status_code not in (200, 204):
                return jsonify({"error": "Failed to assign role", "details": role_response.text}), 400

        return jsonify({"message": "User created successfully", "user_id": user_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
