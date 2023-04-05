# returns data escaped from html
def escape_html(data: str) -> str:
    return data.replace("&", "&amp").replace("<", "&lt").replace(">", "&gt")


# returns true if the username is alphanumeric and has acceptable length ( 3 <= len <= 20)
def valid_username(username: str) -> bool:
    if not username.isalnum():
        return False
    if not len(username) >= 3:
        return False
    if not len(username) <= 20:
        return False


# returns true if password is 8 - 20 characters long
def valid_password(password: str) -> bool:
    if not len(password) >= 8:
        return False
    if not len(password) <= 20:
        return False
