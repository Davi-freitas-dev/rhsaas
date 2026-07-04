(function () {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  function serviceWorkerUrl() {
    if (!window.trustedTypes) {
      return "/sw.js";
    }

    const policy =
      window.rhSaasTrustedTypesPolicy ||
      window.trustedTypes.createPolicy("rhsaas", {
        createScriptURL: function (url) {
          if (url === "/sw.js") {
            return url;
          }

          throw new TypeError("URL de service worker não permitida.");
        },
      });

    window.rhSaasTrustedTypesPolicy = policy;
    return policy.createScriptURL("/sw.js");
  }

  window.addEventListener("load", function () {
    navigator.serviceWorker.register(serviceWorkerUrl(), { scope: "/" }).catch(function () {
      // A instalacao continua disponivel quando o navegador conseguir carregar o service worker.
    });
  });
})();
