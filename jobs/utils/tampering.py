import base64
import hashlib
import sys
import urllib.parse

tamper_known_values = ['aliases', 'data_base64', 'php_octal', 'space2tab', 'url']


class TamperingHandler:
    def __init__(self, tamper_list):
        self.invoke = []
        self.__tamper_list = tamper_list

        if tamper_list == "":
            return

        operations = tamper_list.split(',')

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
        return word.replace(' ', '\u0009')

    def _ifs(self, word):
        return word.replace(' ', '${IFS}')

    def _url(self, word):
        return urllib.parse.quote(word)

    def _aliases(self, word):
        return word.replace("<tab>", "\u0009") \
                     .replace("<q>", "\u0027") \
                     .replace("<m>", "-") \
                     .replace("<er>", "2>&1") \
                     .replace("<cr>", "%0d%0a") \
                     .replace("<rc>", "%0a%0d")

    def _data_base64(self, word):
        return f'data://text/plain;base64,{self._base64(word)}'

    def _base64(self, word):
        return base64.b64encode(word.encode()).decode('utf-8')

    def _md5(self, word):
        md5 = hashlib.md5()
        md5.update(word.encode())
        return md5.hexdigest()

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

    def __str__(self):
        return self.__tamper_list

