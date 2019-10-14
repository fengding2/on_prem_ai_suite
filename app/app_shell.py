import cmd

class AppShell(cmd.Cmd):
    intro = 'Welcome to the on-prem AI shell.\n Type help or ? to list commands.\n'
    prompt = '(on-prem) '

    pass




if __name__ == "__main__":
    AppShell().cmdloop()