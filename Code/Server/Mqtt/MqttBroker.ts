const mqtt = require('mqtt');

class MqttBroker {

    // createMqttClient
    public createMqttClient(host: any, onconnect: any) {
            const client = mqtt.connect(host);

            client.on('connect', () => {
                if (onconnect)
                    onconnect();
            });

        return client
    }

    // createSubscriber
    public async createSubscriber(host: any, topic: string, onconnect: null, onerr: any, onmessage: any) {


        const client = await this.createMqttClient(host, onconnect);

        client.subscribe(topic, onerr);
        client.on('message', onmessage);

        return client;
    }

    // createMqttClient
    public async createPublisher(host: any, topic: string, onconnect: null, message: object, close: true)  {

        const client = await this.createMqttClient(host, onconnect);

        client.publish(topic, message);

        if (close)
            client.end();

        return client;
    }


}