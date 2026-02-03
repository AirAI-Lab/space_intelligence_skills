package mqtt

import (
    mqtt "github.com/eclipse/paho.mqtt.golang"
    "log"
    "time"
)

// Client MQTT客户端
type Client struct {
    client    mqtt.Client
    brokerURL string
    clientID  string
    username  string
    password  string
}

// NewClient 创建MQTT客户端
func NewClient(brokerURL, clientID, username, password string) *Client {
    opts := mqtt.NewClientOptions()
    opts.AddBroker(brokerURL)
    opts.SetClientID(clientID)
    opts.SetUsername(username)
    opts.SetPassword(password)
    opts.SetKeepAlive(60 * time.Second)
    opts.SetPingTimeout(10 * time.Second)
    opts.SetOnConnectHandler(func(c mqtt.Client) {
        log.Printf("MQTT connected to %s", brokerURL)
    })
    opts.SetAutoReconnect(true)
    opts.SetMaxReconnectInterval(10 * time.Second)

    return &Client{
        client:    mqtt.NewClient(opts),
        brokerURL: brokerURL,
        clientID:  clientID,
        username:  username,
        password:  password,
    }
}

// Connect 连接
func (c *Client) Connect() error {
    if token := c.client.Connect(); token.Wait() && token.Error() != nil {
        return token.Error()
    }
    return nil
}

// Subscribe 订阅主题
func (c *Client) Subscribe(topic string, qos byte, handler mqtt.MessageHandler) error {
    if token := c.client.Subscribe(topic, qos, handler); token.Wait() && token.Error() != nil {
        return token.Error()
    }
    log.Printf("Subscribed to topic: %s", topic)
    return nil
}

// Publish 发布消息
func (c *Client) Publish(topic string, qos byte, retained bool, payload interface{}) error {
    token := c.client.Publish(topic, qos, retained, payload)
    token.Wait()
    return token.Error()
}

// Disconnect 断开连接
func (c *Client) Disconnect() {
    c.client.Disconnect(250)
}
