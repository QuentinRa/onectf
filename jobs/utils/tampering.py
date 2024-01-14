import base64
import sys
import urllib.parse

tamper_known_values = ['aliases', 'data_base64', 'php_octal', 'space2tab', 'url']


class TamperingHandler:
    def __init__(self, tamper_list):
        if tamper_list == "":
            return
        operations = tamper_list.split(',')
        self.invoke = []

        for operation in operations:
            operation = "_" + operation
            if hasattr(self, operation):
                method = getattr(self, operation)
                self.invoke.append(method)
            else:
                print(f"[ERROR] The tamper operation <{operation}> does not exist.")
                sys.exit(2)

    def apply(self, word):
        for method in self.invoke:
            word = method(word)

        return word

    def _space2tab(self, word):
        return word.replace(' ', '<tab>')

    def _url(self, word):
        return urllib.parse.quote(word)

    def _aliases(self, word):
        return word.replace("<tab>", "\u0009") \
                     .replace("<q>", "\u0027") \
                     .replace("<m>", "-") \
                     .replace("<er>", "2>&1") \
                     .replace("<cr>", "%0d%0a")

    def _data_base64(self, word):
        encoded_contents = base64.b64encode(word.encode()).decode('utf-8')
        return f'data://text/plain;base64,{encoded_contents}'

    def _php_octal(self, word):
        """
        Dummy function.
        Encode each word using octal and quote it.
        """
        encoded = ''
        first_letter = True
        had_letter = False
        for letter in word:
            if letter.isalpha():
                if first_letter:
                    encoded += '"'
                    first_letter = False
                    had_letter = True
                encoded += "\\" + oct(ord(letter))
            else:
                if had_letter:
                    encoded += '"'
                    had_letter = False
                encoded += letter
        if had_letter:
            encoded += '"'
        return encoded.replace("\\0o", "\\")

