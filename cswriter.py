from contextlib import contextmanager

class CSWriter:
    text = ""
    indent = 0

    def write(self, text):
        self.text += text

    def write_indents(self):
        if self.text == "":
            self.text = "    " * self.indent
        else:
            self.text += "\n" + "    " * self.indent

    def write_indented(self, text):
        self.write_indents()
        self.write(text)

    @contextmanager
    def delimit(self, start, end):
        self.write(start)
        yield
        self.write(end)

    @contextmanager
    def delimit_if(self, start, end, bool):
        if not bool:
            yield
            return

        self.write(start)
        yield
        self.write(end)

    @contextmanager
    def delimit_args(self):
        with self.delimit("(", ")"):
            yield

    @contextmanager
    def delimit_generic(self):
        with self.delimit("<", ">"):
            yield

    def enumerate_join(self, elements, delim):
        count = 0
        for element in elements:
            if count > 0:
                self.write(delim)

            yield element
            count += 1

    @contextmanager
    def block(self):
        self.write_indented("{")
        self.indent += 1
        yield
        self.indent -= 1
        self.write_indented("}")

    def build(self):
        return self.text
