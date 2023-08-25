from colorama import init, Fore

init()


class logger:
    @staticmethod
    def info(info):
        """Out put info message"""
        print(f"{Fore.BLUE}INFO{Fore.WHITE}:     {info}")

    @staticmethod
    def input_text_(input_text):
        """Input text"""
        _in = input(f"INPUT     {input_text}")
        return _in

    @staticmethod
    def success(success):
        """Out put success message"""
        print(f"{Fore.GREEN}SUCCESS{Fore.WHITE}:  {success}")

    @staticmethod
    def error(error):
        """Out put error message"""
        print(f"{Fore.RED}ERROR{Fore.WHITE}:    {error}")

    @staticmethod
    def warning(warning):
        """Out put warning message"""
        print(f"{Fore.YELLOW}WARNING{Fore.WHITE}:  {warning}")
