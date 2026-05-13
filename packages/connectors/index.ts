import type { ConnectorMetadata } from "../shared";

export type InboundConnectorResult = {
  raw_payload: string;
  normalized_payload?: string;
  metadata: ConnectorMetadata;
};

export type OutboundReceipt = {
  receipt_id: string;
  target_type: string;
  packet_type: string;
  timestamp: string;
  status: string;
  mock: boolean;
};
