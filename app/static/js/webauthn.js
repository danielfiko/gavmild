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
    const successContainer = $(".status-message-success")
    const errorContainer = $(".status-message-error")

    // Reset success/error messages
    elemSuccess.innerHTML = '';
    elemError.innerHTML = '';
    successContainer.hide()
    errorContainer.hide()

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
        elemError.innerText = 'Feil: Sikkerhetsnøkkelen er antakeligvis allerede registrert.';
    } else {
        elemError.innerText = error;
    }
    errorContainer.show();
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
    // Check HTTP status rather than consuming body twice
    if (verificationResp.ok) {
        const htmlContent = await verificationResp.text();
        $(".add-key-container").html(htmlContent)
    } else {
        const verificationJSON = await verificationResp.json();
        elemError.innerText = (verificationJSON && verificationJSON.msg)
            ? verificationJSON.msg
            : 'Oisann, noe gikk galt! Prøv igjen.';
        errorContainer.show();
    }
}

function nameSecurityKey() {

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
    const resp = await fetch('/webauthn/authentication-options', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({email: $("#email").val()}),
    });

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
        elemError.innerText = (verificationJSON && verificationJSON.msg)
            ? verificationJSON.msg
            : 'Oh no, something went wrong!';
    }
}