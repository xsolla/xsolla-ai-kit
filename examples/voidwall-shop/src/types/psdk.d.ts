import 'react';

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements {
      'psdk-total': any;
      'psdk-legal': any;
      'psdk-payment-methods': any;
      'psdk-payment-form-messages': any;
      'psdk-status': any;
    }
  }
}
