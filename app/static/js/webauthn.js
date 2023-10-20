$(document).ready(function() {
    const { browserSupportsWebAuthn } = SimpleWebAuthnBrowser;
    if (browserSupportsWebAuthn()) {
        $(".webauthn-login").css("display", "flex")
        $("#webauth-authenticate").on("click", handleLogin)
        $("#webauth-register").on("click", handleRegistration)
    }
})

// Start registration when the user clicks a button
async function handleRegistration() {
    const {startRegistration} = SimpleWebAuthnBrowser;
    const elemSuccess = document.getElementById('success');
    const elemError = document.getElementById('error');
    // Reset success/error messages
    elemSuccess.innerHTML = '';
    elemError.innerHTML = '';

    // GET registration options from the endpoint that calls
    // @simplewebauthn/server -> generateRegistrationOptions()
    const resp = await fetch('/webauthn/registration-options');

    let attResp;
    try {
    // Pass the options to the authenticator and wait for a response
    attResp = await startRegistration(await resp.json());
    } catch (error) {
    // Some basic error handling
    if (error.name === 'InvalidStateError') {
        elemError.innerText = 'Error: Authenticator was probably already registered by user';
    } else {
        elemError.innerText = error;
    }

    throw error;
    }

    // POST the response to the endpoint that calls
    // @simplewebauthn/server -> verifyRegistrationResponse()
    const verificationResp = await fetch('/webauthn/registration-verification', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(attResp),
    });

    // Wait for the results of verification
    const verificationJSON = await verificationResp.json();

    // Show UI appropriate for the `verified` status
    if (verificationJSON && verificationJSON.verified) {
    elemSuccess.innerHTML = 'Passordløs innloggin ble lagt til!';
    } else {
    elemError.innerHTML = `Oisann, noe gikk galt! Feilmelding: <pre>${JSON.stringify(
        verificationJSON,
    )}</pre>`;
    }
}

async function handleLogin() {
    const {startAuthentication} = SimpleWebAuthnBrowser;
    const elemSuccess = document.getElementById('success');
    const elemError = document.getElementById('error');
    // Reset success/error messages
    elemSuccess.innerHTML = '';
    elemError.innerHTML = '';

    // GET authentication options from the endpoint that calls
    // @simplewebauthn/server -> generateAuthenticationOptions()
    const resp = await fetch('/webauthn/authentication-options');

    let asseResp;
    try {
    // Pass the options to the authenticator and wait for a response
    asseResp = await startAuthentication(await resp.json());
    } catch (error) {
    // Some basic error handling
    elemError.innerText = error;
    throw error;
    }

    // POST the response to the endpoint that calls
    // @simplewebauthn/server -> verifyAuthenticationResponse()
    const verificationResp = await fetch('/webauthn/authentication-verification', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(asseResp),
    });

    // Wait for the results of verification
    const verificationJSON = await verificationResp.json();

    // Show UI appropriate for the `verified` status
    if (verificationJSON && verificationJSON.verified) {
        if (verificationJSON.redirect) {
            // Redirect the user to a different page
            window.location.href = verificationJSON.redirect;
        }
    // elemSuccess.innerHTML = 'Success!';
    } else {
    elemError.innerHTML = `Oh no, something went wrong! Response: <pre>${JSON.stringify(
        verificationJSON,
    )}</pre>`;
    }
}