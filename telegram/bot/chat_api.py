import openai


class OpenaiError(Exception):
    pass


def read_secret(secret_name):
    try:
        with open(f"/run/secrets/{secret_name}", "r") as secret_file:
            return secret_file.read().strip()
    except IOError:
        return None

sys_msg = "You are a chatbot that reluctantly answers with a sarcastic responses, helping users with the correct use of chat commands. You do not ask if they need any further assistance."

def openai_api(prompt, sys_msg=sys_msg, temp=1.0):
    openai.api_key = read_secret("openai-token")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=temp,
            max_tokens=256
        )
        return response['choices'][0]['message']['content']
    except openai.error.Timeout as e:
        # Handle timeout error, e.g. retry or log
        raise OpenaiError(f"OpenAI API request timed out: {e}")
        pass
    except openai.error.APIError as e:
        # Handle API error, e.g. retry or log
        raise OpenaiError(f"OpenAI API returned an API Error: {e}")
        pass
    except openai.error.APIConnectionError as e:
        # Handle connection error, e.g. check network or log
        raise OpenaiError(f"OpenAI API request failed to connect: {e}")
        pass
    except openai.error.InvalidRequestError as e:
        # Handle invalid request error, e.g. validate parameters or log
        raise OpenaiError(f"OpenAI API request was invalid: {e}")
        pass
    except openai.error.AuthenticationError as e:
        # Handle authentication error, e.g. check credentials or log
        raise OpenaiError(f"OpenAI API request was not authorized: {e}")
        pass
    except openai.error.PermissionError as e:
        # Handle permission error, e.g. check scope or log
        raise OpenaiError(f"OpenAI API request was not permitted: {e}")
        pass
    except openai.error.RateLimitError as e:
        # Handle rate limit error, e.g. wait or log
        raise OpenaiError(f"OpenAI API request exceeded rate limit: {e}")
        pass
