import sys


class TamperingHandler:
    def __init__(self, tamper_list):
        if tamper_list == "":
            return
        operations = tamper_list.split(',')
        self.invoke = []
        self._encode_url = False

        for operation in operations:
            operation = "_" + operation
            if operation == "_url":
                self._encode_url = True
            elif hasattr(self, operation):
                method = getattr(self, operation)
                self.invoke.append(method)
            else:
                print(f"[ERROR] The tamper operation <{operation}> does not exist.")
                sys.exit(2)

    def apply(self, word):
        for method in self.invoke:
            word = method(word)

        return word

    def encode_url(self):
        return self._encode_url

    def _space2tab(self, word):
        return word.replace(' ', '<tab>')

    def _aliases(self, word):
        return word.replace("<tab>", "\u0009") \
                     .replace("<q>", "\u0027") \
                     .replace("<m>", "-") \
                     .replace("<er>", "2>&1") \
                     .replace("<cr>", "%0d%0a")

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

