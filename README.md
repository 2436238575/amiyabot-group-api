# Kubernetes Probes

该插件没有任何外显功能，他的作用是提供了两个可以匿名访问的HTTP请求：

|  Url   | Method  | 说明  |
|  ----  | ----  | ----  |
| /probes/readiness  | GET | 在本插件的load函数被调用后变为200OK，在这之前返回404NotFound |
| /probes/liveness  | GET | 维护一个内部状态，每当bot收到一条消息则变为True，该接口被调用一次后变回False。调用接口时，为True则返回200OK，为False返回404NotFound |

这两个接口的目的可以为诸如Kubernetes的Pod等提供ReadinessProbe和LivenessProbe

不过，如果你的bot访问的人比较少，或者所处的群说话的人少，那么LivenessProbe会变得不是很可靠。

建议根据实际情况调整LivenessProbe的timeoutSeconds，或者用readiness作为LivenessProbe来探测诸如死机OOM等严重问题。

```

readinessProbe:
    httpGet:
    path: /probes/readiness
    port: 5080
    initialDelaySeconds: 30
    timeoutSeconds: 30
livenessProbe:
    httpGet:
    path: /probes/liveness
    port: 5080
    initialDelaySeconds: 120
    timeoutSeconds: 120

```

|  版本   | 变更  |
|  ----  | ----  |
| 1.0  | 最初的版本 |
| 1.1  | 适配新版兔兔 |