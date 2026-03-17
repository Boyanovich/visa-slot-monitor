# Visa slot monitor

An automated scraper and notification system for visa appointment slots. Built with Selenium, the script monitors the target website for changes and pushes real-time availability updates directly to a Telegram bot.

The site uses reCAPTCHA. To bypass it without paying for third-party solving APIs, the script selects the audio challenge, downloads the mp3, and uses OpenAI's Whisper model locally to transcribe the audio and pass the captcha. 

Files:
- `visa_checker.py`: The main scraper and captcha solver.
- `subscription_bot.py`: A basic Telegram bot to manage who gets the notifications.

### Setup & Run
Make sure you have `ffmpeg` installed on your system (Whisper needs it to process audio).

1. `pip install -r requirements.txt`
2. Put your Telegram bot token in both `.py` files.
3. The visa website uses dynamic session tokens. You need to log in manually in your browser, copy the URL with the `?t=` parameter, and paste it into `URL_TO_CHECK` inside `visa_checker.py`.
4. Run `python subscription_bot.py` and send `/start` to your bot in Telegram.
5. Run `python visa_checker.py` and leave it running.