import type { D1Like } from "../../../packages/memory/src/store.js";
export interface QueueMessage<T=unknown>{body:T;ack():void;retry(options?:{delaySeconds?:number}):void;}
export interface MessageBatch<T=unknown>{messages:QueueMessage<T>[];}
export interface QueueBinding{send(message:unknown):Promise<void>;}
export interface AssetsBinding{fetch(request:Request):Promise<Response>;}
export interface ServiceBindingLike{fetch(input:Request|string,init?:RequestInit):Promise<Response>;}
export interface DurableObjectStorageLike{sql:{exec(query:string,...bindings:unknown[]):{toArray():unknown[]}};}
export interface DurableObjectStateLike{storage:DurableObjectStorageLike;}
export interface DurableObjectStubLike{fetch(input:Request|string,init?:RequestInit):Promise<Response>;}
export interface DurableObjectNamespaceLike{idFromName(name:string):unknown;get(id:unknown):DurableObjectStubLike;}
export interface WorkflowInstanceLike{id:string;sendEvent(event:{type:string;payload:unknown}):Promise<void>;}
export interface WorkflowBindingLike{create(options:{id?:string;params:{taskId:string;kind:string;approvalId?:string}}):Promise<WorkflowInstanceLike>;get(id:string):WorkflowInstanceLike;}
export interface Env{DB:D1Like;EFFECTS?:ServiceBindingLike;MODELS?:ServiceBindingLike;EVENTS_QUEUE?:QueueBinding;ASSETS?:AssetsBinding;COORDINATOR?:DurableObjectNamespaceLike;COMPUTE_GOVERNOR?:DurableObjectNamespaceLike;BUSINESS_WORKFLOW?:WorkflowBindingLike;ADMIN_TOKEN_HASH?:string;WEBHOOK_SECRET?:string;APPROVAL_SIGNING_KEY?:string;EXECUTOR_SIGNING_KEY?:string;ARIA_GIT_SHA?:string;ENVIRONMENT?:string;}