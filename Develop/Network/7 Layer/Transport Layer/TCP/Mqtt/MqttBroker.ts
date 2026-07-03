const mqtt = require('mqtt');

interface MqttConfig {
    host: string;
    port?: number;
    protocol?: 'mqtt' | 'mqtts' | 'ws' | 'wss';
    username?: string;
    password?: string;
    clientId?: string;
}

interface MqttMessage {
    topic: string;
    payload: string | Buffer;
    qos?: 0 | 1 | 2;
    retain?: boolean;
}

class MqttBroker {
    private static instance: MqttBroker;
    private client: any = null;
    private isConnected: boolean = false;
    private reconnectAttempts: number = 0;
    private readonly maxReconnectAttempts: number = 5;
    private readonly reconnectInterval: number = 5000; // 5 seconds

    private constructor() {}

    public static getInstance(): MqttBroker {
        if (!MqttBroker.instance) {
            MqttBroker.instance = new MqttBroker();
        }
        return MqttBroker.instance;
    }

    private createClientOptions(config: MqttConfig): any {
        return {
            host: config.host,
            port: config.port || 1883,
            protocol: config.protocol || 'mqtt',
            username: config.username,
            password: config.password,
            clientId: config.clientId || `mqtt_client_${Math.random().toString(16).substr(2, 8)}`,
            clean: true,
            reconnectPeriod: this.reconnectInterval,
            connectTimeout: 30 * 1000, // 30 seconds
        };
    }

    public async connect(config: MqttConfig): Promise<void> {
        if (this.client && this.isConnected) {
            return;
        }

        return new Promise((resolve, reject) => {
            try {
                const options = this.createClientOptions(config);
                this.client = mqtt.connect(options);

                this.client.on('connect', () => {
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    console.log('MQTT Client connected successfully');
                    resolve();
                });

                this.client.on('error', (error: Error) => {
                    console.error('MQTT Client error:', error);
                    reject(error);
                });

                this.client.on('close', () => {
                    this.isConnected = false;
                    console.log('MQTT Client disconnected');
                });

                this.client.on('reconnect', () => {
                    this.reconnectAttempts++;
                    if (this.reconnectAttempts > this.maxReconnectAttempts) {
                        console.error('Max reconnection attempts reached');
                        this.disconnect();
                    }
                });

            } catch (error) {
                reject(error);
            }
        });
    }

    public async subscribe(topic: string, options?: any): Promise<void> {
        if (!this.client || !this.isConnected) {
            throw new Error('MQTT Client is not connected');
        }

        return new Promise((resolve, reject) => {
            this.client.subscribe(topic, options || {}, (error: Error) => {
                if (error) {
                    reject(error);
                } else {
                    console.log(`Subscribed to topic: ${topic}`);
                    resolve();
                }
            });
        });
    }

    public async publish(message: MqttMessage, options?: any): Promise<void> {
        if (!this.client || !this.isConnected) {
            throw new Error('MQTT Client is not connected');
        }

        return new Promise((resolve, reject) => {
            this.client.publish(
                message.topic,
                message.payload,
                options || { qos: 0, retain: false },
                (error: Error) => {
                    if (error) {
                        reject(error);
                    } else {
                        console.log(`Published to topic: ${message.topic}`);
                        resolve();
                    }
                }
            );
        });
    }

    public onMessage(callback: (topic: string, message: Buffer) => void): void {
        if (!this.client) {
            throw new Error('MQTT Client is not initialized');
        }
        this.client.on('message', callback);
    }

    public async disconnect(): Promise<void> {
        if (!this.client) {
            return;
        }

        return new Promise((resolve) => {
            this.client.end(true, () => {
                this.isConnected = false;
                this.client = null;
                console.log('MQTT Client disconnected');
                resolve();
            });
        });
    }

    public isClientConnected(): boolean {
        return this.isConnected;
    }
}

export default MqttBroker;