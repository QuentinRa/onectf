import base64
import hashlib
import sys
import urllib.parse

tamper_known_values = ['aliases', 'base64', 'data_base64', 'php_octal', 'space2tab', 'url']


class TamperingHandler:
    def __init__(self, tamper_list):
        self.invoke = []
        self.__tamper_list = tamper_list

        if tamper_list == "":
            return

        operations = tamper_list.split(',')

        for operation in operations:
            _operation = "_" + operation
            if hasattr(self, _operation):
                method = getattr(self, _operation)
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
                     .replace("<crlf>", "%0d%0a") \
                     .replace("<lf>", "%0a")

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

    def _php_base_convert(self, word):
        """Experimental, require testing"""
        encoded = ''
        first_letter = True
        for letter in word:
            if letter.isalpha() or letter in ['.']:
                if not first_letter:
                    encoded += '.'
                encoded += f"base_convert({ord(letter) - ord('a') + 10},10,36)" if letter.isalpha() else "(pi().pi())[1]"
                first_letter = False
            else:
                #print("> Not encoded:", letter)
                encoded += letter
                first_letter = True
        return encoded

    def __str__(self):
        return self.__tamper_list

