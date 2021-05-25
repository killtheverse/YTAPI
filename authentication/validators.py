from rest_framework import serializers


class CustomPasswordValidator():
    def __init__(self, min_length=1, min_password_length=8):
        self.min_length = min_length
        self.min_password_length = min_password_length
    def validate(self, password):
        special_characters = "[~\!@#\$%\^&\*\(\)_\+{}\":;'\[\]]"
        if len(password)<self.min_password_length:
            return f'password should be atleast {self.min_password_length} symbols'
        if not any(char.isdigit() for char in password):
            return f'password must contain atleast {self.min_length} digit'
        if not any(char.isalpha() for char in password):
            return f'password must contain atleast {self.min_length} character'
        if not any(char in special_characters for char in password):
            return f'password must contain atleast {self.min_length} special character'
        return None


class CustomUsernameValidator():
    def __init__(self, min_username_length=3, max_username_length=100):
        self.min_username_length = min_username_length
        self.max_username_length = max_username_length
    
    def validate(self, username):
        special_characters = "[~\!@#\$%\^&\*\(\) \+{}\":;'\[\]]"
        if len(username) > self.max_username_length:
            return f'username should be atmost {self.max_username_length} symbols'
        if len(username) < self.min_username_length:
            return f'username should be at least {self.min_username_length} symbols'
        if any(char in special_characters for char in username):
            return 'username should not contain any special characters'
        return None