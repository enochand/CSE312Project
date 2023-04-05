# returns data escaped from html
def escape_html(data: str) -> str:
    return data.replace("&", "&amp").replace("<", "&lt").replace(">", "&gt")


# returns true if the username is alphanumeric and has acceptable length ( 3 <= len <= 20)
def valid_username(username: str) -> bool:
    if not username.isalnum():
        return False
    if len(username) < 3:
        return False
    if len(username) > 20:
        return False
    return True


# returns true if password is 8 - 20 characters long
def valid_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if len(password) > 20:
        return False
    return True
