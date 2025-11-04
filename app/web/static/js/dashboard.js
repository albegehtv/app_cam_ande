(function () {
    const form = document.getElementById('camera-settings-form');
    if (!form) {
        return;
    }

    const buttons = Array.from(form.querySelectorAll('[data-endpoint]'));
    const sourceInput = document.getElementById('camera-source');
    const frameSkipInput = document.getElementById('camera-frame-skip');
    const confidenceInput = document.getElementById('camera-confidence');
    const statusPill = document.querySelector('[data-status-pill]');
    const sourceDisplay = document.querySelector('[data-camera-source]');
    const lastConnectionDisplay = document.querySelector('[data-camera-last-connection]');
    const confidenceDisplay = document.querySelector('[data-camera-confidence]');
    const frameSkipDisplay = document.querySelector('[data-camera-frame-skip]');
    const feedbackBox = document.querySelector('[data-camera-feedback]');
    const errorBox = document.querySelector('[data-camera-error]');

    function setLoading(isLoading) {
        buttons.forEach((button) => {
            button.disabled = isLoading;
        });
        form.classList.toggle('is-loading', isLoading);
    }

    function toNumber(value) {
        if (value === '' || value === null || typeof value === 'undefined') {
            return undefined;
        }
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : undefined;
    }

    function buildPayload() {
        const payload = {};
        const source = sourceInput.value.trim();
        if (source) {
            payload.source = source;
        }

        const frameSkip = toNumber(frameSkipInput.value);
        if (typeof frameSkip !== 'undefined') {
            payload.frame_skip = Math.trunc(frameSkip);
        }

        const minConfidence = toNumber(confidenceInput.value);
        if (typeof minConfidence !== 'undefined') {
            payload.min_confidence = minConfidence;
        }

        return payload;
    }

    function updateStatusPill(state) {
        if (!statusPill) {
            return;
        }
        statusPill.textContent = state.connected ? 'Conectada' : 'Desconectada';
        statusPill.classList.toggle('connected', Boolean(state.connected));
        statusPill.classList.toggle('disconnected', !state.connected);
    }

    function updateDisplays(state) {
        if (sourceDisplay) {
            sourceDisplay.textContent = state.source || '—';
        }
        if (lastConnectionDisplay) {
            lastConnectionDisplay.textContent = state.last_connected_at || '—';
        }
        if (confidenceDisplay) {
            confidenceDisplay.textContent = Number.isFinite(state.min_confidence)
                ? state.min_confidence.toFixed(2)
                : '—';
        }
        if (frameSkipDisplay) {
            frameSkipDisplay.textContent = state.frame_skip ?? '—';
        }
        if (typeof state.source === 'string') {
            sourceInput.value = state.source;
        }
        if (typeof state.frame_skip !== 'undefined') {
            frameSkipInput.value = state.frame_skip;
        }
        if (typeof state.min_confidence !== 'undefined') {
            confidenceInput.value = state.min_confidence.toFixed(2);
        }
    }

    function showFeedback(message) {
        if (feedbackBox) {
            feedbackBox.textContent = message || '';
        }
    }

    function showError(message) {
        if (errorBox) {
            errorBox.textContent = message || '';
        }
    }

    function extractMessage(error) {
        if (error instanceof Error && error.message) {
            return error.message;
        }
        if (typeof error === 'string' && error.length > 0) {
            return error;
        }
        return 'Ocurrió un error inesperado.';
    }

    async function requestCamera(endpoint, method, payload) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: payload ? JSON.stringify(payload) : undefined,
        };

        if (!payload) {
            delete options.body;
        }

        const response = await fetch(endpoint, options);
        if (!response.ok) {
            const detail = await response.json().catch(() => ({}));
            const message = detail.detail || 'No se pudo comunicar con la cámara.';
            throw new Error(message);
        }
        return response.json();
    }

    async function handleAction(action) {
        setLoading(true);
        showFeedback('');
        showError('');
        try {
            let endpoint = '/api/camera';
            let method = 'PATCH';
            let payload = buildPayload();

            if (action === 'connect') {
                endpoint = '/api/camera/connect';
                method = 'POST';
            } else if (action === 'disconnect') {
                endpoint = '/api/camera/disconnect';
                method = 'POST';
                payload = undefined;
            }

            const state = await requestCamera(endpoint, method, payload);
            updateStatusPill(state);
            updateDisplays(state);
            if (state.last_error) {
                showError(state.last_error);
            } else {
                const message =
                    action === 'connect'
                        ? 'Cámara conectada correctamente.'
                        : action === 'disconnect'
                        ? 'Se ha desconectado la cámara.'
                        : 'Configuración actualizada.';
                showFeedback(message);
            }
        } catch (error) {
            showError(extractMessage(error));
        } finally {
            setLoading(false);
        }
    }

    async function refreshState() {
        try {
            const state = await requestCamera('/api/camera', 'GET');
            updateStatusPill(state);
            updateDisplays(state);
            if (state.last_error) {
                showError(state.last_error);
            }
        } catch (error) {
            showError(extractMessage(error));
        }
    }

    buttons.forEach((button) => {
        button.addEventListener('click', () => handleAction(button.dataset.endpoint));
    });

    refreshState();
})();
