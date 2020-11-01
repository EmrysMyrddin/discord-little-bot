import unittest

import websocket

from discord import Bot


class BotTest(unittest.TestCase):
    def test_run_without_registered_command(self):
        class MyBot(Bot):
            pass

        with self.assertRaises(ValueError):
            MyBot.run()

    def test_register_commands(self):
        class MyBot(Bot):
            @Bot.register_command('!test')
            def handle_test_command(self): pass

            @Bot.register_command('!test2')
            def handle_test_command2(self): pass

        self.assertEqual(2, len(MyBot._discord_commands))

    def test_run(self):
        TestBot.run("NzcxODgxNzY1NTg5NjE0NjQy.X5yk6Q.8alrAzo4lCXySTkUIxYo8CfKZPs")


class TestBot(Bot):
    @Bot.register_command('!test', cooldown=10)
    def handle_test_command(self, message):
        print("WOW WOW WOW", message.content)
        message.respond('oui ?')


if __name__ == '__main__':
    unittest.main()
    websocket.enableTrace(True)
